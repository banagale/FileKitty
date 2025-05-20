import atexit
import os
from datetime import datetime
from pathlib import Path

# Unused standard library imports removed: ast, hashlib, json, os, sys, uuid
# Keep existing PyQt5 imports and add new ones
from PyQt5.QtCore import QSettings, QSize, QStandardPaths, Qt, QTimer
from PyQt5.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QGuiApplication,
    QIcon,
    QKeySequence,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,  # For QStyle, QKeySequence.Quit
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from filekitty.constants import (
    ICON_PATH,
    SETTINGS_DEFAULT_PATH_KEY,  # Used by FilePicker via HistoryManager, but PreferencesDialog needs it too
    # HISTORY_DIR_NAME, # Only used by HistoryManager & PreferencesDialog
    # STALE_CHECK_INTERVAL_MS, # Only used by HistoryManager
    # HASH_ERROR_SENTINEL, # Only used by HistoryManager
    # HASH_MISSING_SENTINEL, # Only used by HistoryManager
    # TEXT_CHECK_CHUNK_SIZE, # Only used by utils.is_text_file
)
from filekitty.core.history_manager import HistoryManager
from filekitty.core.python_parser import extract_code_and_imports, parse_python_file
from filekitty.core.utils import (
    detect_language,
    is_text_file,
    read_file_contents,
    sanitize_path,
)  # Added sanitize_path, detect_language
from filekitty.ui.dialogs import PreferencesDialog, SelectClassesFunctionsDialog
from filekitty.ui.qt_widgets import DragOutButton

# from filekitty.core.utils import is_text_file # Already imported


# --- Main Application Window ---
class FilePicker(QWidget):
    def __init__(self, initial_files: list[str] | None = None):
        super().__init__()
        self.setWindowTitle("FileKitty")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setGeometry(100, 100, 900, 700)  # Increased default width slightly
        self.setAcceptDrops(True)  # Allow dropping files onto the main window
        self.currentFiles: list[str] = []
        self.selected_items: list[str] = []
        self.selection_mode: str = "All Files"  # or "Single File"
        self.selected_file: str | None = None  # Path of the single selected file
        self._dragged_out_temp_files: list[str] = []  # Track temp files for cleanup

        self.history_manager = HistoryManager(self)

        # --- Load preferences for timestamps ---
        settings = QSettings("Bastet", "FileKitty")
        self.include_date_modified = settings.value("includeDateModified", "true") == "true"
        self.use_llm_timestamp = settings.value("useLlmTimestamp", "false") == "true"

        self.staleCheckTimer = QTimer(self)
        self.staleCheckTimer.timeout.connect(self._poll_stale_status)  # Connection confirmed
        if self.history_manager.get_history_dir():
            self.staleCheckTimer.start(self.history_manager.get_stale_check_interval())  # Use manager's interval

        self.initUI()
        self.createActions()
        self.populateToolbar()
        self.createMenu()
        self._update_history_ui()  # Initialize history button states etc.

        # Register cleanup functions for application exit
        atexit.register(self.history_manager.cleanup_history_files)  # Delegated
        atexit.register(self._cleanup_drag_out_files)

        # --- open any files passed in on launch (Dock / Cmd-Tab) ---
        if initial_files:
            self._update_files_and_maybe_create_state(sorted(initial_files))

    def handle_external_file(self, file_path: str):
        """Handles files opened via Dock or Finder."""
        # You could add logic to append to the current file list or replace:
        self._update_files_and_maybe_create_state([file_path])

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)  # Use full window space

        # Toolbar
        self.toolbar = QToolBar("History Toolbar")
        self.toolbar.setIconSize(QSize(22, 22))
        self.mainLayout.addWidget(self.toolbar)

        # Central Widget Area (holds file list and text edit)
        centralWidget = QWidget()
        centralLayout = QVBoxLayout(centralWidget)
        self.mainLayout.addWidget(centralWidget, 1)  # Give it stretch factor

        # File List
        self.fileList = QListWidget(self)
        centralLayout.addWidget(self.fileList)  # Add to central layout

        # Text Edit Area
        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setFontFamily("Menlo")  # Use a monospaced font
        centralLayout.addWidget(self.textEdit, 1)  # Give textEdit stretch factor

        # --- Action Buttons Layout ---
        actionButtonLayout = QHBoxLayout()
        actionButtonLayout.setContentsMargins(5, 5, 5, 5)  # Add some padding

        btnOpen = QPushButton("📂 Select Files", self)
        btnOpen.setToolTip("Open the file selection dialog")
        btnOpen.clicked.connect(self.openFiles)
        actionButtonLayout.addWidget(btnOpen)

        self.btnSelectClassesFunctions = QPushButton("🔍 Select Code", self)
        self.btnSelectClassesFunctions.setToolTip("Select specific classes/functions from Python files")
        self.btnSelectClassesFunctions.clicked.connect(self.selectClassesFunctions)
        self.btnSelectClassesFunctions.setEnabled(False)  # Disabled initially
        actionButtonLayout.addWidget(self.btnSelectClassesFunctions)

        self.btnRefresh = QPushButton("🔄 Refresh", self)
        self.btnRefresh.setToolTip("Reload content from the selected files")
        self.btnRefresh.clicked.connect(self.refreshText)
        self.btnRefresh.setEnabled(False)  # Disabled initially
        actionButtonLayout.addWidget(self.btnRefresh)

        self.btnCopy = QPushButton("📋 Copy", self)
        self.btnCopy.setToolTip("Copy the generated text to the clipboard")
        self.btnCopy.clicked.connect(self.copyToClipboard)
        self.btnCopy.setEnabled(False)  # Disabled initially
        actionButtonLayout.addWidget(self.btnCopy)

        # --- Auto-Copy Checkbox ---
        self.autoCopyCheckBox = QCheckBox("Auto-Copy", self)
        self.autoCopyCheckBox.setToolTip(
            "When checked, copies output to the clipboard automatically after loading files."
        )
        # Load from QSettings
        settings = QSettings("Bastet", "FileKitty")
        auto_copy_value = settings.value("autoCopyOnImport")
        if auto_copy_value is None:
            self.auto_copy = True
        else:
            self.auto_copy = auto_copy_value == "true"
        self.autoCopyCheckBox.setChecked(self.auto_copy)
        # Connect to toggle handler
        self.autoCopyCheckBox.stateChanged.connect(self.toggleAutoCopy)
        actionButtonLayout.addWidget(self.autoCopyCheckBox)

        # --- Drag Out Button ---
        self.btnDragOut = DragOutButton(self.textEdit, self)
        self.btnDragOut.setEnabled(False)  # Disabled initially
        actionButtonLayout.addWidget(self.btnDragOut)

        actionButtonLayout.addStretch()  # Push buttons to the left

        self.mainLayout.addLayout(actionButtonLayout)  # Add buttons below central widget

        # Status Bar Layout
        statusBarLayout = QHBoxLayout()
        statusBarLayout.setContentsMargins(5, 2, 5, 2)  # Small margins
        self.lineCountLabel = QLabel("Lines: 0")
        statusBarLayout.addWidget(self.lineCountLabel)
        self.mainLayout.addLayout(statusBarLayout)  # Add status bar at the bottom

        # Connect signals
        self.textEdit.textChanged.connect(self.updateLineCountAndActionButtons)  # Updated method name
        self.setLayout(self.mainLayout)

    def toggleAutoCopy(self, state):
        self.auto_copy = state == Qt.Checked
        settings = QSettings("Bastet", "FileKitty")
        settings.setValue("autoCopyOnImport", "true" if self.auto_copy else "false")
        print(f"Auto-Copy preference updated: {self.auto_copy}")

    def createActions(self):
        # History Navigation
        icon_back = QApplication.style().standardIcon(QStyle.SP_ArrowBack)
        self.backAction = QAction(icon_back, "Back", self)
        self.backAction.setShortcut(QKeySequence.Back)
        self.backAction.setToolTip("Go to previous state (Cmd+[ or Alt+Left)")
        self.backAction.triggered.connect(self.go_back)
        self.backAction.setEnabled(False)

        icon_forward = QApplication.style().standardIcon(QStyle.SP_ArrowForward)
        self.forwardAction = QAction(icon_forward, "Forward", self)
        self.forwardAction.setShortcut(QKeySequence.Forward)
        self.forwardAction.setToolTip("Go to next state (Cmd+] or Alt+Right)")
        self.forwardAction.triggered.connect(self.go_forward)
        self.forwardAction.setEnabled(False)

        # Application Menu Actions
        self.prefAction = QAction("Preferences...", self)
        self.prefAction.setShortcut(QKeySequence.Preferences)
        self.prefAction.triggered.connect(self.showPreferences)

        self.quitAction = QAction("Quit FileKitty", self)
        self.quitAction.setShortcut(QKeySequence.Quit)
        self.quitAction.triggered.connect(QApplication.instance().quit)

    def populateToolbar(self):
        self.toolbar.addAction(self.backAction)
        self.toolbar.addAction(self.forwardAction)
        self.toolbar.addSeparator()

        self.historyStatusLabel = QLabel("History: 0 of 0")
        self.historyStatusLabel.setToolTip("Current position in history")
        self.historyStatusLabel.setContentsMargins(5, 0, 5, 0)  # Add spacing
        self.toolbar.addWidget(self.historyStatusLabel)

        # Stale Indicator (initially hidden)
        self.staleIndicatorLabel = QLabel("")
        self.staleIndicatorLabel.setToolTip(
            "Indicates if file contents have changed, are missing, or had errors since capture"
        )
        self.staleIndicatorLabel.setStyleSheet("color: orange; font-weight: bold; margin-left: 10px;")  # Added margin
        self.toolbar.addWidget(self.staleIndicatorLabel)
        self.staleIndicatorLabel.hide()

        # Spacer to push subsequent items (if any) to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

    def createMenu(self):
        menubar = QMenuBar(self)
        self.mainLayout.setMenuBar(menubar)  # Attach menubar to the main layout

        # App Menu (e.g., FileKitty on macOS)
        appMenu = menubar.addMenu("FileKitty")  # Use app name directly
        appMenu.addAction(self.prefAction)
        appMenu.addSeparator()
        appMenu.addAction(self.quitAction)

        # History Menu
        historyMenu = menubar.addMenu("History")
        historyMenu.addAction(self.backAction)
        historyMenu.addAction(self.forwardAction)

    def showPreferences(self):
        current_default_path = self.get_default_path()
        current_history_base_path = self.history_manager.get_history_base_path()  # Use HistoryManager's getter
        dialog = PreferencesDialog(current_default_path, current_history_base_path, self)
        if dialog.exec_():
            # Settings are saved within the dialog's accept() method
            # Check if the history path setting actually triggered a change
            settings = QSettings("Bastet", "FileKitty")
            self.include_date_modified = settings.value("includeDateModified", "true") == "true"
            self.use_llm_timestamp = settings.value("useLlmTimestamp", "false") == "true"

            if dialog.history_path_changed:
                print("History path setting changed.")
                new_history_base_path = dialog.get_history_base_path()
                self._change_history_directory(new_history_base_path)

    def _change_history_directory(self, new_base_path: str):
        """Handles changing the history storage location by delegating to HistoryManager."""
        self.history_manager.change_history_directory(new_base_path)

    def show_message_box(self, type_str: str, title: str, text: str):
        """Wrapper for showing QMessageBox, callable by HistoryManager."""
        if type_str == "critical":
            QMessageBox.critical(self, title, text)
        elif type_str == "warning":
            QMessageBox.warning(self, title, text)
        elif type_str == "information":
            QMessageBox.information(self, title, text)
        else:  # Default to information
            QMessageBox.information(self, title, text)

    def get_default_path(self):
        """Gets the default path for file dialogs from settings or system default."""
        settings = QSettings("Bastet", "FileKitty")
        default_docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        # Return stored path, fallback to Documents, fallback to home
        return settings.value(SETTINGS_DEFAULT_PATH_KEY, default_docs or str(Path.home()))

    def openFiles(self):
        default_path = self.get_default_path()
        options = QFileDialog.Options()
        # Example filter, can be expanded
        file_filter = (
            "All Files (*);;"
            "Python Files (*.py);;"
            "JavaScript Files (*.js);;"
            "TypeScript Files (*.ts *.tsx);;"
            "Text Files (*.txt *.md);;"
            "Configuration (*.json *.yaml *.yml *.toml *.ini)"
        )
        files, _ = QFileDialog.getOpenFileNames(self, "Select files", default_path, file_filter, options=options)
        if files:
            # Process selected files
            self._update_files_and_maybe_create_state(sorted(files))

    def _update_files_and_maybe_create_state(self, files: list[str]):
        """Updates the internal file list and UI, then creates a history state."""
        self.currentFiles = files
        # Reset selections when file list changes significantly
        self.selected_items = []
        self.selection_mode = "All Files"
        self.selected_file = None

        self._update_ui_for_new_files()  # Update the QListWidget
        self.updateTextEdit()  # Update the QTextEdit content
        self.history_manager.create_new_state(  # Delegated
            self.currentFiles, self.selected_items, self.selection_mode, self.selected_file, is_text_file
        )

        # auto-copy combined output if the setting is enabled
        if getattr(self, "auto_copy", False):
            self.copyToClipboard()

    def _update_ui_for_new_files(self):
        """Populates the file list widget based on self.currentFiles."""
        self.fileList.clear()
        has_files = bool(self.currentFiles)
        has_python_text_files = False

        for file_path in self.currentFiles:
            display_text = sanitize_path(file_path)  # Use util function

            item = QListWidgetItem(display_text)

            is_txt = is_text_file(file_path)
            if not is_txt:
                # Grey out and disable non-text files slightly differently
                item.setForeground(QColor(Qt.gray))
                item.setToolTip("Binary or non-standard text file, content not shown.")
            elif file_path.endswith(".py"):
                has_python_text_files = True

            self.fileList.addItem(item)

        # Enable "Select Code" only if there are Python text files
        self.btnSelectClassesFunctions.setEnabled(has_python_text_files)
        self.btnRefresh.setEnabled(has_files)

    def selectClassesFunctions(self):
        """Opens the dialog to select specific classes/functions from Python files."""
        all_classes, all_functions, parse_errors = {}, {}, []

        # Parse only the Python files that are also text files
        python_text_files = [f for f in self.currentFiles if f.endswith(".py") and is_text_file(f)]

        if not python_text_files:
            QMessageBox.information(self, "No Files", "No Python text files are currently selected to analyze.")
            return

        for file_path in python_text_files:
            try:
                classes, functions, _, _ = parse_python_file(file_path)
                # Use file path as key
                all_classes[file_path] = classes
                all_functions[file_path] = functions
            except Exception as e:
                parse_errors.append(f"{Path(file_path).name}: {e}")

        if parse_errors:
            QMessageBox.warning(self, "Parsing Error", "Could not parse some files:\n" + "\n".join(parse_errors))

        # Check if any symbols were found across all parsable files
        # Note: all_classes/all_functions keys are file paths, check values
        found_symbols = any(v for v in all_classes.values()) or any(v for v in all_functions.values())
        if not found_symbols and not parse_errors:
            QMessageBox.information(
                self, "No Symbols Found", "No Python classes or functions found in the selected files."
            )
            return  # Don't show dialog if nothing to select

        # Store current state to detect changes
        old_selected_items = set(self.selected_items)
        old_mode, old_file = self.selection_mode, self.selected_file

        # Show the dialog, passing the file-keyed dictionaries
        dialog = SelectClassesFunctionsDialog(all_classes, all_functions, self.selected_items, self)
        if dialog.exec_():  # User clicked OK
            new_selected_items, new_mode, new_file = (
                dialog.get_selected_items(),
                dialog.get_mode(),
                dialog.get_selected_file(),
            )

            # Check if the selection state actually changed
            state_changed = (
                set(new_selected_items) != old_selected_items
                or new_mode != old_mode
                or new_file != old_file  # Comparing paths directly
            )

            if state_changed:
                self.selected_items, self.selection_mode, self.selected_file = new_selected_items, new_mode, new_file
                self.updateTextEdit()  # Regenerate text output
                self.history_manager.create_new_state(  # Delegated
                    self.currentFiles, self.selected_items, self.selection_mode, self.selected_file, is_text_file
                )

    def copyToClipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.textEdit.toPlainText())

    def updateLineCountAndActionButtons(self):
        """Updates the line count label and enables/disables relevant action buttons."""
        text = self.textEdit.toPlainText()
        # Count non-empty lines more efficiently
        line_count = 0
        if text:
            line_count = sum(1 for line in text.splitlines() if line.strip())

        self.lineCountLabel.setText(f"Lines: {line_count}")

        has_text = bool(text)
        self.btnCopy.setEnabled(has_text)
        self.btnDragOut.setEnabled(has_text)  # Enable Drag Out button based on text presence

    def refreshText(self):
        """Reloads content from the current file list and updates the text view."""
        print("Refreshing content...")  # Add some feedback
        try:
            self.updateTextEdit()  # Re-process files
            # Check if content *actually* changed before creating new state? Optional optimization.
            self.history_manager.create_new_state(  # Delegated
                self.currentFiles, self.selected_items, self.selection_mode, self.selected_file, is_text_file
            )
        except Exception as e:
            QMessageBox.warning(self, "Refresh Error", f"Failed to refresh files: {str(e)}")
            print(f"Refresh error details: {e}")  # Log details

    def updateTextEdit(self):
        """Generates the combined text output based on current files and selections."""
        if self.history_manager.is_loading_state():  # Use HistoryManager's state
            return

        combined_code, files_to_process, parse_errors = "", [], []

        # Determine which files to process based on selection mode
        if self.selection_mode == "Single File" and self.selected_file:
            # Check if selected file is still in the main list and is a text file
            if self.selected_file in self.currentFiles and is_text_file(self.selected_file):
                files_to_process = [self.selected_file]
            else:
                # Handle case where selected file is no longer valid or not text
                reason = "not found" if self.selected_file not in self.currentFiles else "not a text file"
                self.textEdit.setPlainText(f"# Error: Selected file {Path(self.selected_file).name} is {reason}.")
                self.updateLineCountAndActionButtons()
                return
        else:  # "All Files" mode
            # Process only text files from the current list
            files_to_process = [f for f in self.currentFiles if is_text_file(f)]

        # Display message if no text files are available to process
        if not files_to_process and self.currentFiles:
            self.textEdit.setPlainText("# No text files selected or available to display content.")
            self.updateLineCountAndActionButtons()
            return
        elif not self.currentFiles:
            self.textEdit.setPlainText("")  # Clear if no files selected at all
            self.updateLineCountAndActionButtons()
            return

        for file_path in files_to_process:
            # --- Skip non-text files (already filtered, but double check) ---
            if not is_text_file(file_path):
                continue  # Should not happen due to pre-filtering, but safe

            current_sanitized_path = sanitize_path(file_path)  # Use util function
            try:
                # Get date modified string for output (LLM-friendly)
                stat = Path(file_path).stat()
                if self.use_llm_timestamp:
                    mtime = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat()
                else:
                    mtime = datetime.fromtimestamp(stat.st_mtime).astimezone().strftime("%b %d, %Y %I:%M %p %Z")

                modified_line_for_output = f"**Last modified: {mtime}**"

            except Exception as e:
                print(f"Warning: Could not retrieve modified time for {file_path}: {e}")
                modified_line_for_output = "**Last modified: ?**"
            try:
                # Process Python files (potentially filtering classes/functions)
                if file_path.endswith(".py"):
                    classes, functions, _, file_content = parse_python_file(file_path)
                    is_filtered = bool(self.selected_items)
                    # Items defined in *this specific file*
                    items_in_this_file = set(classes) | set(functions)

                    # Determine if filtering applies to *this specific file*
                    # Does this file contain any of the globally selected items?
                    relevant_items_exist_in_file = any(item in items_in_this_file for item in self.selected_items)

                    should_filter_this_file = is_filtered and (
                        self.selection_mode == "Single File" or relevant_items_exist_in_file
                    )

                    if should_filter_this_file:
                        # Determine *which* items to extract from this file
                        items_to_extract = (
                            # In Single File mode, try extracting all globally selected items (if they exist here)
                            [item for item in self.selected_items if item in items_in_this_file]
                            if self.selection_mode == "Single File"
                            # In All Files mode, extract only the selected items present in this file
                            else [item for item in self.selected_items if item in items_in_this_file]
                        )

                        if items_to_extract:  # Only proceed if there are relevant items to extract
                            filtered_code = extract_code_and_imports(
                                file_content, items_to_extract, current_sanitized_path, modified_line_for_output
                            )
                            if filtered_code.strip():  # Add only if extraction yielded something
                                combined_code += filtered_code + "\n\n"  # Add extra newline between extracts
                        # If filtering yields nothing for this file, we implicitly skip its content

                    else:  # Not filtering this Python file, include its whole content
                        combined_code += (
                            f"# {current_sanitized_path}\n"
                            f"{modified_line_for_output}\n\n"
                            f"```python\n"
                            f"{file_content.strip()}\n"
                            f"```\n\n"
                        )

                # Process other (text) file types
                else:
                    file_content = read_file_contents(file_path)
                    lang = detect_language(file_path)  # Use util function
                    combined_code += (
                        f"# {current_sanitized_path}\n{modified_line_for_output}\n\n```{lang}\n"
                        f"{file_content.strip()}\n```\n\n"
                    )

            except FileNotFoundError:
                parse_errors.append(f"{current_sanitized_path}: File not found")
            except Exception as e:
                # Catch parsing or reading errors
                parse_errors.append(f"{current_sanitized_path}: Error processing - {e}")

        # Update the text edit widget
        self.textEdit.setPlainText(combined_code.strip())
        # updateLineCountAndActionButtons is called automatically via textChanged signal

        # Show accumulated errors, if any
        if parse_errors:
            QMessageBox.warning(
                self, "Processing Errors", "Errors occurred for some files:\n" + "\n".join(parse_errors)
            )

    def dragEnterEvent(self, event: QDragEnterEvent):
        # Accept the drag event if it contains URLs (files or directories)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        # Handle the drop event when items are released onto the window
        if event.mimeData().hasUrls():
            files_to_add = []
            dropped_urls = event.mimeData().urls()

            for url in dropped_urls:
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    path_obj = Path(local_path)

                    if path_obj.is_dir():
                        # Recursively walk the directory, respecting symlinks option
                        print(f"Scanning directory: {local_path}")
                        try:
                            # followlinks=False to prevent infinite loops with symlinks
                            for root, dirs, filenames in os.walk(local_path, followlinks=False):
                                # Optional: Skip hidden directories (like .git, .svn)
                                dirs[:] = [d for d in dirs if not d.startswith(".")]
                                for filename in filenames:
                                    # Optional: Skip hidden files
                                    if filename.startswith("."):
                                        continue
                                    file_path = os.path.join(root, filename)
                                    # Double check it's a file and not a broken symlink etc.
                                    if Path(file_path).is_file():
                                        files_to_add.append(file_path)
                        except OSError as e:
                            print(f"Error walking directory {local_path}: {e}")
                            QMessageBox.warning(
                                self, "Directory Error", f"Error scanning directory:\n{local_path}\n{e}"
                            )

                    elif path_obj.is_file():
                        # Add individual files
                        files_to_add.append(local_path)
                    else:
                        print(f"Skipping dropped item (not a file or directory): {local_path}")

            if files_to_add:
                # Remove duplicates and sort
                unique_files = sorted(list(set(files_to_add)))
                print(f"Adding {len(unique_files)} unique files from drop.")
                self._update_files_and_maybe_create_state(unique_files)
                event.acceptProposedAction()
                return  # Indicate drop was handled

        print("Drop event ignored (no valid local file URLs).")
        event.ignore()  # Ignore if not handled

    # --- History Management ---
    # _calculate_file_hash, _create_new_state, _load_state, _check_stale_status
    # are now primarily in HistoryManager. FilePicker will call them.

    def _apply_loaded_state_data(self, state_data: dict | None):
        """Applies the data from a loaded history state to FilePicker."""
        if not state_data:
            return

        # _is_loading_state is managed by history_manager.load_state()
        # No need to set it here explicitly if load_state handles it via try...finally
        try:
            self.currentFiles = state_data.get("files", [])
            self.selected_items = state_data.get("selected_items", [])
            self.selection_mode = state_data.get("selection_mode", "All Files")
            self.selected_file = state_data.get("selected_file", None)

            self._update_ui_for_new_files()
            self.updateTextEdit()
            # UI updates like _update_history_ui and stale status are handled in go_back/go_forward
            # after state is applied.
        except Exception as e:  # Catch any error during state application
            print(f"Error applying loaded state data: {e}")
            # Optionally, show a message to the user
            self.show_message_box("warning", "State Load Error", f"Could not fully apply the loaded state: {e}")

    def go_back(self):
        """Navigates to the previous state in history."""
        current_index, _ = self.history_manager.get_history_info()
        if current_index > 0:
            new_index = current_index - 1
            state_data = self.history_manager.load_state(new_index)
            if state_data:
                self._apply_loaded_state_data(state_data)
                self._update_history_ui()  # Update UI based on new index
                current_stale_check_data = self.history_manager.get_current_state_data()
                if current_stale_check_data:
                    stale_status = self.history_manager.check_stale_status(current_stale_check_data, is_text_file)
                    self._update_stale_status_display(stale_status)
                else:
                    self._update_stale_status_display({})

    def go_forward(self):
        """Navigates to the next state in history."""
        current_index, history_count = self.history_manager.get_history_info()
        if current_index < history_count - 1:
            new_index = current_index + 1
            state_data = self.history_manager.load_state(new_index)
            if state_data:
                self._apply_loaded_state_data(state_data)
                self._update_history_ui()  # Update UI based on new index
                current_stale_check_data = self.history_manager.get_current_state_data()
                if current_stale_check_data:
                    stale_status = self.history_manager.check_stale_status(current_stale_check_data, is_text_file)
                    self._update_stale_status_display(stale_status)
                else:
                    self._update_stale_status_display({})

    def _update_history_ui(self):
        """Updates history-related UI elements (buttons, status label)."""
        idx, count = self.history_manager.get_history_info()
        can_go_back = idx > 0
        can_go_forward = idx < count - 1

        self.backAction.setEnabled(can_go_back)
        self.forwardAction.setEnabled(can_go_forward)

        current_pos = idx + 1 if count > 0 else 0
        self.historyStatusLabel.setText(f"History: {current_pos} of {count}")

    def _poll_stale_status(self):
        """Periodically checks if the current history state's files are stale."""
        # history_manager._is_loading_state is an internal detail, use public getter
        if (
            self.history_manager.is_loading_state()
            or not self.history_manager.get_history_dir()
            or not self.history_manager.get_history()
            or self.history_manager.get_history_index() < 0
        ):
            if self.staleIndicatorLabel.isVisible():  # Only update if it was visible
                self._update_stale_status_display({})
            return

        current_state_data = self.history_manager.get_current_state_data()
        if current_state_data:
            stale_status = self.history_manager.check_stale_status(current_state_data, is_text_file)
            self._update_stale_status_display(stale_status)
        else:
            self._update_stale_status_display({})  # Clear display if no current state

    def _update_stale_status_display(self, stale_status: dict):
        """Updates the UI label to indicate file staleness."""
        if not stale_status:
            self.staleIndicatorLabel.hide()
            self.staleIndicatorLabel.setText("")
            self.staleIndicatorLabel.setToolTip("")
            return

        statuses = stale_status.values()
        if "missing" in statuses:
            display_text = "Files Missing!"
        elif "error" in statuses:
            display_text = "File Errors!"
        elif "modified" in statuses:
            display_text = "Files Modified"
        else:
            display_text = "Files Changed (?)"

        tooltip_lines = ["Files have changed since this history state was captured:"]
        for path in sorted(stale_status.keys()):
            status = stale_status[path]
            sanitized = sanitize_path(path)  # Use util function
            tooltip_lines.append(f"- {sanitized} ({status})")
        tooltip = "\n".join(tooltip_lines)

        self.staleIndicatorLabel.setText(f"⚠️ {display_text}")
        self.staleIndicatorLabel.setToolTip(tooltip)
        self.staleIndicatorLabel.show()

    # _cleanup_history_files is now fully in HistoryManager and registered via
    # atexit(self.history_manager.cleanup_history_files)

    def _cleanup_drag_out_files(self):
        """Removes temporary files created by the DragOutButton."""
        if not self._dragged_out_temp_files:
            return  # Nothing to clean

        print(f"Cleaning up {len(self._dragged_out_temp_files)} temporary drag-out files...")
        cleaned_count = 0
        error_count = 0
        for file_path in self._dragged_out_temp_files:
            try:
                if os.path.exists(file_path):  # Check if it still exists
                    os.remove(file_path)
                    cleaned_count += 1
            except OSError as e:
                print(f"Error removing temporary drag file {file_path}: {e}")
                error_count += 1
        print(f"Removed {cleaned_count} temporary drag-out files.")
        if error_count:
            print(f"Failed to remove {error_count} temporary drag files.")
        self._dragged_out_temp_files = []  # Clear the list
