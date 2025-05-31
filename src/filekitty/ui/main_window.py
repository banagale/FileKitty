import os
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QSettings, QSize, QStandardPaths, Qt, QTimer
from PyQt5.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QGuiApplication,
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
    SETTINGS_DEFAULT_PATH_KEY,
    SETTINGS_TREE_BASE_KEY,
    SETTINGS_TREE_ENABLED_KEY,
    SETTINGS_TREE_IGNORE_KEY,
    TREE_IGNORE_DEFAULT,
)
from filekitty.core.history_manager import HistoryManager
from filekitty.core.project_tree import generate_tree
from filekitty.core.python_parser import extract_code_and_imports, parse_python_file
from filekitty.core.utils import (
    detect_language,
    is_text_file,
    read_file_contents,
    sanitize_path,
)  # Added sanitize_path, detect_language
from filekitty.ui.dialogs import PreferencesDialog, SelectClassesFunctionsDialog
from filekitty.ui.qt_widgets import DragOutButton


# --- Main Application Window ---
class FilePicker(QWidget):
    def __init__(self, initial_files: list[str] | None = None):
        super().__init__()

        self._generate_tree = generate_tree  # lazy

        # ---- window basics ----
        self.setWindowTitle("FileKitty")
        from PyQt5.QtGui import QIcon  # keep import

        from filekitty.constants import ICON_PATH

        self.setWindowIcon(QIcon(ICON_PATH))
        self.setGeometry(100, 100, 900, 700)
        self.setAcceptDrops(True)

        # ---- core state ----
        self.currentFiles: list[str] = []
        self.selected_items: list[str] = []
        self.selection_mode: str = "All Files"
        self.selected_file: str | None = None
        self._dragged_out_temp_files: list[str] = []  # <— restored
        self.current_tree_snapshot: dict | None = None

        # ---- prefs ----
        stg = QSettings("Bastet", "FileKitty")
        self.include_tree = stg.value(SETTINGS_TREE_ENABLED_KEY, "true") == "true"
        self.tree_base_dir = stg.value(SETTINGS_TREE_BASE_KEY, "")
        self.tree_ignore_regex = stg.value(SETTINGS_TREE_IGNORE_KEY, TREE_IGNORE_DEFAULT)

        self.include_date_modified = stg.value("includeDateModified", "true") == "true"
        self.use_llm_timestamp = stg.value("useLlmTimestamp", "false") == "true"

        # ---- managers / timers ----
        self.history_manager = HistoryManager(self)
        self.staleCheckTimer = QTimer(self)
        self.staleCheckTimer.timeout.connect(self._poll_stale_status)
        if self.history_manager.get_history_dir():
            self.staleCheckTimer.start(self.history_manager.get_stale_check_interval())

        # ---- build UI ----
        self.initUI()
        self.createActions()
        self.populateToolbar()
        self.createMenu()
        self._update_history_ui()

        # ---- cleanup hooks ----
        import atexit

        atexit.register(self.history_manager.cleanup_history_files)
        atexit.register(self._cleanup_drag_out_files)

        # ---- initial files ----
        if initial_files:
            self._update_files_and_maybe_create_state(sorted(initial_files))

    def handle_external_file(self, file_path: str):
        """Handles files opened via Dock or Finder."""
        # You could add logic to append to the current file list or replace:
        self._update_files_and_maybe_create_state([file_path])

    # ───────────────── Tree helpers ───────────────── #

    def _toggle_tree_enabled(self, state):
        self.include_tree = state == Qt.Checked
        QSettings("Bastet", "FileKitty").setValue(SETTINGS_TREE_ENABLED_KEY, "true" if self.include_tree else "false")
        if self.currentFiles:
            self.refreshText()

    def _open_tree_settings(self):
        from filekitty.ui.tree_settings_dialog import TreeSettingsDialog

        dlg = TreeSettingsDialog(self)
        if dlg.exec_():  # user pressed OK
            stg = QSettings("Bastet", "FileKitty")
            self.tree_base_dir = stg.value(SETTINGS_TREE_BASE_KEY, "")
            self.tree_ignore_regex = stg.value(SETTINGS_TREE_IGNORE_KEY, TREE_IGNORE_DEFAULT)
            if self.currentFiles:
                self.refreshText()

    def _snapshot_tree(self) -> dict | None:
        """Return a fresh tree snapshot or None if disabled/unavailable."""
        if not self.include_tree:
            return None
        base = self.tree_base_dir or (os.path.commonpath(self.currentFiles) if self.currentFiles else "")
        if not base:
            return None
        try:
            md_text, snap = self._generate_tree(base, self.tree_ignore_regex)
            self.current_tree_snapshot = snap
            return snap
        except Exception as e:
            print(f"Tree generation failed: {e}")
            return None

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

        # --- Folder Tree Controls ---
        treeRow = QHBoxLayout()
        treeRow.setContentsMargins(5, 5, 5, 5)  # ← add (same padding as action buttons)

        self.treeCheck = QCheckBox("Include File Tree", self)
        self.treeCheck.setChecked(self.include_tree)
        self.treeCheck.stateChanged.connect(self._toggle_tree_enabled)
        treeRow.addWidget(self.treeCheck)

        treeGear = QPushButton("🛠", self)
        treeGear.setFixedWidth(40)
        treeGear.setStyleSheet("padding: 6px 8px 6px 8px;")
        treeGear.setToolTip("Configure tree base & ignore list")
        treeGear.clicked.connect(self._open_tree_settings)
        treeRow.addWidget(treeGear)

        treeRow.addStretch()
        self.mainLayout.addLayout(treeRow)

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
        self.current_tree_snapshot = None
        # Reset selections when file list changes significantly
        self.selected_items = []
        self.selection_mode = "All Files"
        self.selected_file = None

        self._update_ui_for_new_files()  # Update the QListWidget
        self.updateTextEdit()  # Update the QTextEdit content
        self.history_manager.create_new_state(  # Delegated
            self.currentFiles,
            self.selected_items,
            self.selection_mode,
            self.selected_file,
            is_text_file,
            tree_snapshot=None,
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
                    self.currentFiles,
                    self.selected_items,
                    self.selection_mode,
                    self.selected_file,
                    is_text_file,
                    tree_snapshot=None,
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
        self.current_tree_snapshot = None
        print("Refreshing content...")  # Add some feedback
        try:
            self.updateTextEdit()  # Re-process files
        except Exception as e:
            QMessageBox.warning(self, "Refresh Error", f"Failed to refresh files: {str(e)}")
            print(f"Refresh error details: {e}")  # Log details

    def updateTextEdit(self):
        """Render folder-tree (if any) + file contents. Does NOT create a history state."""
        if self.history_manager.is_loading_state():
            return

        # ────────── Decide which tree snapshot to use ──────────
        if self.current_tree_snapshot:  # coming from history navigation
            tree_snap = self.current_tree_snapshot
        else:  # fresh view / refresh
            tree_snap = self._snapshot_tree()  # may be None
            if tree_snap:  # cache for possible reuse
                self.current_tree_snapshot = tree_snap

        tree_md = tree_snap["rendered"] if tree_snap else ""

        # ────────── Existing file-concatenation logic (unaltered) ──────────
        combined_code, files_to_process, parse_errors = "", [], []

        # Which files should we include?
        if self.selection_mode == "Single File" and self.selected_file:
            if self.selected_file in self.currentFiles and is_text_file(self.selected_file):
                files_to_process = [self.selected_file]
            else:
                reason = "not found" if self.selected_file not in self.currentFiles else "not a text file"
                self.textEdit.setPlainText(f"# Error: Selected file {Path(self.selected_file).name} is {reason}.")
                self.updateLineCountAndActionButtons()
                return
        else:
            files_to_process = [f for f in self.currentFiles if is_text_file(f)]

        if not files_to_process and self.currentFiles:
            self.textEdit.setPlainText("# No text files selected or available to display content.")
            self.updateLineCountAndActionButtons()
            return
        elif not self.currentFiles:
            self.textEdit.setPlainText("")
            self.updateLineCountAndActionButtons()
            return

        for file_path in files_to_process:
            if not is_text_file(file_path):
                continue

            current_sanitized_path = sanitize_path(file_path)
            try:
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
                if file_path.endswith(".py"):
                    classes, functions, _, file_content = parse_python_file(file_path)
                    is_filtered = bool(self.selected_items)
                    items_in_this_file = set(classes) | set(functions)
                    relevant_items = any(item in items_in_this_file for item in self.selected_items)
                    should_filter = is_filtered and (self.selection_mode == "Single File" or relevant_items)

                    items_to_extract = []  # ensure defined for all code paths
                    if should_filter:
                        items_to_extract = [item for item in self.selected_items if item in items_in_this_file]
                        if items_to_extract:
                            filtered_code = extract_code_and_imports(
                                file_content,
                                items_to_extract,
                                current_sanitized_path,
                                modified_line_for_output,
                            )
                            if filtered_code.strip():
                                combined_code += filtered_code + "\n\n"
                    else:
                        combined_code += (
                            f"# {current_sanitized_path}\n"
                            f"{modified_line_for_output}\n\n"
                            f"```python\n{file_content.strip()}\n```\n\n"
                        )
                else:
                    file_content = read_file_contents(file_path)
                    lang = detect_language(file_path)
                    combined_code += (
                        f"# {current_sanitized_path}\n{modified_line_for_output}\n\n"
                        f"```{lang}\n{file_content.strip()}\n```\n\n"
                    )

            except FileNotFoundError:
                parse_errors.append(f"{current_sanitized_path}: File not found")
            except Exception as e:
                parse_errors.append(f"{current_sanitized_path}: Error processing - {e}")

        # ────────── Merge tree + files and show ──────────
        parts = [p for p in (tree_md, combined_code.strip()) if p]
        self.textEdit.setPlainText("\n\n".join(parts))

        # Line-count / button updates fire via textChanged signal

        if parse_errors:
            QMessageBox.warning(
                self,
                "Processing Errors",
                "Errors occurred for some files:\n" + "\n".join(parse_errors),
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
            self.selected_file = state_data.get("selected_file")
            self.current_tree_snapshot = state_data.get("tree")

            # Sync checkbox to stored snapshot
            self.include_tree = bool(self.current_tree_snapshot)
            self.treeCheck.setChecked(self.include_tree)

            self._update_ui_for_new_files()
            self.updateTextEdit()
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
