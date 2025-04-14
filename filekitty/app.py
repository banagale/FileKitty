import ast
import atexit
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QSettings, QSize, QStandardPaths, Qt, QTimer
from PyQt5.QtGui import QColor, QDragEnterEvent, QDropEvent, QGuiApplication, QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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

ICON_PATH = "assets/icon/FileKitty-icon.png"
HISTORY_DIR_NAME = "FileKittyHistory"
STALE_CHECK_INTERVAL_MS = 2500  # Check every 2.5 seconds
HASH_ERROR_SENTINEL = "HASH_ERROR"
HASH_MISSING_SENTINEL = "FILE_MISSING"
SETTINGS_DEFAULT_PATH_KEY = "defaultPath"
SETTINGS_HISTORY_PATH_KEY = "historyPath"
TEXT_CHECK_CHUNK_SIZE = 1024  # Bytes to read for text file check


# --- Helper Function ---
def is_text_file(file_path: str) -> bool:
    """
    Attempts to determine if a file is likely a text file.
    Checks for null bytes in the initial chunk and attempts UTF-8 decoding.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(TEXT_CHECK_CHUNK_SIZE)
            if b"\x00" in chunk:
                return False  # Null byte suggests binary
            # Try decoding as UTF-8. If it fails, likely not standard text.
            try:
                chunk.decode("utf-8")
                return True
            except UnicodeDecodeError:
                # Could try other encodings, but for simplicity, assume non-text
                return False
    except OSError:  # UP024: Catch OSError base class for IO/FileNotFound etc.
        # Cannot read or access, treat as non-text for safety
        return False
    except Exception:
        # Catch any other unexpected errors during check
        return False


# --- Dialogs ---
class PreferencesDialog(QDialog):
    def __init__(self, current_default_path, current_history_base_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(500)
        self.initial_default_path = current_default_path
        self.initial_history_base_path = current_history_base_path
        self.initUI()
        self.defaultPathEdit.setText(current_default_path)
        self.historyPathEdit.setText(current_history_base_path)

    def initUI(self):
        mainLayout = QVBoxLayout(self)
        formLayout = QFormLayout()
        self.defaultPathEdit = QLineEdit(self)
        self.defaultPathEdit.setPlaceholderText("Leave blank to use system default (e.g., Documents)")
        self.defaultPathEdit.setToolTip("The starting directory for the 'Select Files' dialog.")
        btnBrowseDefault = QPushButton("Browse...")
        btnBrowseDefault.clicked.connect(self.browseDefaultPath)
        defaultPathLayout = QHBoxLayout()
        defaultPathLayout.addWidget(self.defaultPathEdit, 1)
        defaultPathLayout.addWidget(btnBrowseDefault)
        formLayout.addRow(QLabel("Default 'Select Files' Directory:"), defaultPathLayout)
        self.historyPathEdit = QLineEdit(self)
        self.historyPathEdit.setPlaceholderText("Leave blank to use default temporary location")
        self.historyPathEdit.setToolTip(f"Folder where history snapshots ({HISTORY_DIR_NAME}) will be stored.")
        btnBrowseHistory = QPushButton("Browse...")
        btnBrowseHistory.clicked.connect(self.browseHistoryPath)
        historyPathLayout = QHBoxLayout()
        historyPathLayout.addWidget(self.historyPathEdit, 1)
        historyPathLayout.addWidget(btnBrowseHistory)
        formLayout.addRow(QLabel("History Storage Directory:"), historyPathLayout)
        mainLayout.addLayout(formLayout)
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        btnSave = QPushButton("Save")
        btnCancel = QPushButton("Cancel")
        buttonLayout.addWidget(btnSave)
        buttonLayout.addWidget(btnCancel)
        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)
        mainLayout.addLayout(buttonLayout)
        self.setLayout(mainLayout)

    def browseDefaultPath(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Default Directory for Opening Files", self.defaultPathEdit.text()
        )
        if dir_path:
            self.defaultPathEdit.setText(dir_path)

    def browseHistoryPath(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Base Directory for History Storage", self.historyPathEdit.text()
        )
        if dir_path:
            self.historyPathEdit.setText(dir_path)

    def get_default_path(self):
        return self.defaultPathEdit.text().strip()

    def get_history_base_path(self):
        return self.historyPathEdit.text().strip()

    def accept(self):
        history_path = self.get_history_base_path()
        if history_path and not os.path.isdir(history_path):
            QMessageBox.warning(self, "Invalid Path", f"History path is not a valid directory:\n{history_path}")
            return
        settings = QSettings("Bastet", "FileKitty")
        settings.setValue(SETTINGS_DEFAULT_PATH_KEY, self.get_default_path())
        settings.setValue(SETTINGS_HISTORY_PATH_KEY, history_path)
        self.history_path_changed = history_path != self.initial_history_base_path
        super().accept()


class SelectClassesFunctionsDialog(QDialog):
    # (No Ruff errors reported here, keeping as is)
    def __init__(self, all_classes, all_functions, selected_items=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Classes/Functions")
        self.all_classes = all_classes
        self.all_functions = all_functions
        self.selected_items = list(selected_items) if selected_items is not None else []
        self.parent = parent  # Reference to the main window (FilePicker)
        self.resize(600, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        mode_layout = QHBoxLayout()
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(["All Files", "Single File"])
        self.mode_combo.currentTextChanged.connect(self.update_file_selection)
        mode_layout.addWidget(QLabel("Selection Mode:"))
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)
        self.file_combo = QComboBox(self)
        self.file_combo.setVisible(False)  # Initially hidden
        self.file_combo.currentTextChanged.connect(self.update_symbols)
        mode_layout.addWidget(self.file_combo)
        self.fileList = QListWidget(self)
        layout.addWidget(self.fileList)
        self.btnOk = QPushButton("OK", self)
        self.btnOk.clicked.connect(self.accept)
        layout.addWidget(self.btnOk)
        self.setLayout(layout)
        # Initialize based on parent state
        initial_mode = self.parent.selection_mode if self.parent else "All Files"
        self.mode_combo.setCurrentText(initial_mode)
        self.update_file_selection(initial_mode)  # Populate lists/combos
        if initial_mode == "Single File" and self.parent and self.parent.selected_file:
            file_name = Path(self.parent.selected_file).name
            if self.file_combo.findText(file_name) != -1:
                self.file_combo.setCurrentText(file_name)

    def update_file_selection(self, mode):
        self.file_combo.setVisible(mode == "Single File")
        self.file_combo.clear()
        if mode == "Single File":
            # Only list Python files available in the parent's current list
            python_files = [f for f in self.parent.currentFiles if f.endswith(".py") and is_text_file(f)]
            if not python_files:
                self.fileList.clear()
                self.fileList.addItem("No Python files available")
            else:
                current_selection_name = Path(self.parent.selected_file).name if self.parent.selected_file else None
                found_match = False
                for f in python_files:
                    name = Path(f).name
                    self.file_combo.addItem(name)
                    if name == current_selection_name:
                        found_match = True
                # Set combo to previously selected file if possible, else first file
                if found_match and current_selection_name:
                    self.file_combo.setCurrentText(current_selection_name)
                elif python_files:
                    self.file_combo.setCurrentIndex(0)
                    self.update_symbols(self.file_combo.currentText())  # Update symbols list
        else:  # All Files mode
            self.populate_all_files()

    def update_symbols(self, file_name):
        # Update the list widget with classes/functions for the selected file
        self.fileList.clear()
        selected_file = next((f for f in self.parent.currentFiles if Path(f).name == file_name), None)
        if selected_file:
            if not is_text_file(selected_file):
                self.fileList.addItem(f"File '{file_name}' is not a text file.")
                return
            try:
                classes, functions, _, _ = parse_python_file(selected_file)
                if not (classes or functions):
                    self.fileList.addItem("No classes or functions found")
                else:
                    for cls in classes:
                        item = QListWidgetItem(f"Class: {cls}")
                        item.setCheckState(Qt.Checked if cls in self.selected_items else Qt.Unchecked)
                        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                        self.fileList.addItem(item)
                    for func in functions:
                        item = QListWidgetItem(f"Function: {func}")
                        item.setCheckState(Qt.Checked if func in self.selected_items else Qt.Unchecked)
                        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                        self.fileList.addItem(item)
            except Exception as e:
                self.fileList.addItem(f"Error parsing file: {e}")
        elif file_name:  # Handle case where file_name is somehow invalid
            self.fileList.addItem(f"File '{file_name}' not found")

    def populate_all_files(self):
        # Populate list widget for "All Files" mode
        self.fileList.clear()
        has_content = False
        current_selection = self.selected_items
        file_symbols = {}  # Store symbols per file {file_path: {"classes": [], "functions": []}}

        for file_path in self.parent.currentFiles:
            if file_path.endswith(".py") and is_text_file(file_path):
                try:
                    classes, functions, _, _ = parse_python_file(file_path)
                    if classes or functions:
                        file_symbols[file_path] = {"classes": classes, "functions": functions}
                        has_content = True
                except Exception:
                    # Silently ignore files that cannot be parsed in "All Files" mode for now
                    pass

        if not has_content:
            self.fileList.addItem("No classes or functions found")
            return

        for file_path, symbols in file_symbols.items():
            file_header = QListWidgetItem(f"File: {Path(file_path).name}")
            file_header.setFlags(file_header.flags() & ~Qt.ItemIsUserCheckable & ~Qt.ItemIsSelectable)
            self.fileList.addItem(file_header)

            if symbols["classes"]:
                class_header = QListWidgetItem("  Classes:")
                class_header.setFlags(file_header.flags())  # Inherit non-interactive flags
                self.fileList.addItem(class_header)
                for cls in symbols["classes"]:
                    item = QListWidgetItem(f"    Class: {cls}")
                    item.setCheckState(Qt.Checked if cls in current_selection else Qt.Unchecked)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    self.fileList.addItem(item)

            if symbols["functions"]:
                func_header = QListWidgetItem("  Functions:")
                func_header.setFlags(file_header.flags())  # Inherit non-interactive flags
                self.fileList.addItem(func_header)
                for func in symbols["functions"]:
                    item = QListWidgetItem(f"    Function: {func}")
                    item.setCheckState(Qt.Checked if func in current_selection else Qt.Unchecked)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    self.fileList.addItem(item)

    def accept(self):
        # Gather selected items from the list widget before closing
        self.selected_items = []
        for i in range(self.fileList.count()):
            item = self.fileList.item(i)
            if item.flags() & Qt.ItemIsUserCheckable:  # Only process checkable items
                if item.checkState() == Qt.Checked:
                    text_content = item.text().strip()
                    # Extract name after "Class: " or "Function: "
                    if ": " in text_content:
                        self.selected_items.append(text_content.split(": ", 1)[1])
        super().accept()

    def get_selected_items(self):
        return self.selected_items

    def get_mode(self):
        return self.mode_combo.currentText()

    def get_selected_file(self):
        if self.mode_combo.currentText() == "Single File":
            file_name = self.file_combo.currentText()
            # Find the full path corresponding to the selected file name
            return next((f for f in self.parent.currentFiles if Path(f).name == file_name), None)
        return None


# --- Main Application Window ---
class FilePicker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileKitty")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setGeometry(100, 100, 900, 700)
        self.setAcceptDrops(True)
        self.currentFiles: list[str] = []
        self.selected_items: list[str] = []
        self.selection_mode: str = "All Files"
        self.selected_file: str | None = None
        self.history_dir: str = ""
        self.history_base_path: str = ""
        self.history: list[dict] = []
        self.history_index: int = -1
        self._is_loading_state: bool = False
        self._determine_and_setup_history_dir()
        self.staleCheckTimer = QTimer(self)
        self.staleCheckTimer.timeout.connect(self._poll_stale_status)
        if self.history_dir:
            self.staleCheckTimer.start(STALE_CHECK_INTERVAL_MS)
        self.initUI()
        self.createActions()
        self.populateToolbar()
        self.createMenu()
        self._update_history_ui()
        atexit.register(self._cleanup_history_files)

    def _determine_and_setup_history_dir(self) -> None:
        """Reads settings and sets up the history directory path."""
        settings = QSettings("Bastet", "FileKitty")
        stored_base_path = settings.value(SETTINGS_HISTORY_PATH_KEY, "")
        base_path_to_use = ""
        if stored_base_path and os.path.isdir(stored_base_path):
            base_path_to_use = stored_base_path
            self.history_base_path = stored_base_path
            print(f"Using user-defined history base path: {base_path_to_use}")
        else:
            temp_loc = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
            if not temp_loc:
                # Fallback logic if standard temp location isn't found
                home_cache = Path.home() / ".cache"
                lib_cache = Path.home() / "Library" / "Caches"  # macOS specific
                if sys.platform == "darwin" and lib_cache.parent.exists():
                    temp_loc = str(lib_cache)
                elif home_cache.parent.exists():
                    temp_loc = str(home_cache)
                else:  # Last resort
                    temp_loc = "."
            base_path_to_use = str(temp_loc)
            self.history_base_path = ""  # Indicate default is used
            print(f"Using default history base path: {base_path_to_use}")

        history_path = Path(base_path_to_use) / HISTORY_DIR_NAME
        try:
            history_path.mkdir(parents=True, exist_ok=True)
            self.history_dir = str(history_path)
            print(f"History directory set to: {self.history_dir}")
        except OSError as e:
            QMessageBox.critical(self, "History Error", f"Could not create history directory:\n{history_path}\n{e}")
            self.history_dir = ""  # Disable history if directory fails

    def _setup_history_dir(self):
        pass  # Replaced by _determine_and_setup_history_dir

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
        self.textEdit.setFontFamily("monospace")  # Use a monospaced font
        centralLayout.addWidget(self.textEdit, 1)  # Give textEdit stretch factor

        # Action Buttons Layout
        actionButtonLayout = QHBoxLayout()
        btnOpen = QPushButton("📂 Select Files", self)
        btnOpen.clicked.connect(self.openFiles)
        actionButtonLayout.addWidget(btnOpen)

        self.btnSelectClassesFunctions = QPushButton("🔍 Select Classes/Functions", self)
        self.btnSelectClassesFunctions.clicked.connect(self.selectClassesFunctions)
        self.btnSelectClassesFunctions.setEnabled(False)  # Disabled initially
        actionButtonLayout.addWidget(self.btnSelectClassesFunctions)

        self.btnRefresh = QPushButton("🔄 Refresh", self)
        self.btnRefresh.clicked.connect(self.refreshText)
        self.btnRefresh.setEnabled(False)  # Disabled initially
        actionButtonLayout.addWidget(self.btnRefresh)

        self.btnCopy = QPushButton("📋 Copy to Clipboard", self)
        self.btnCopy.clicked.connect(self.copyToClipboard)
        self.btnCopy.setEnabled(False)  # Disabled initially
        actionButtonLayout.addWidget(self.btnCopy)

        self.mainLayout.addLayout(actionButtonLayout)  # Add buttons below central widget

        # Status Bar Layout
        statusBarLayout = QHBoxLayout()
        statusBarLayout.setContentsMargins(5, 2, 5, 2)  # Small margins
        self.lineCountLabel = QLabel("Lines: 0")
        statusBarLayout.addWidget(self.lineCountLabel)
        self.mainLayout.addLayout(statusBarLayout)  # Add status bar at the bottom

        # Connect signals
        self.textEdit.textChanged.connect(self.updateLineCountAndCopyButton)
        self.setLayout(self.mainLayout)

    def createActions(self):
        # History Navigation
        icon_back = QApplication.style().standardIcon(QStyle.SP_ArrowBack)
        self.backAction = QAction(icon_back, "Back", self)
        self.backAction.setShortcut(QKeySequence.Back)
        self.backAction.setToolTip("Go to previous state (Cmd+[)")
        self.backAction.triggered.connect(self.go_back)
        self.backAction.setEnabled(False)

        icon_forward = QApplication.style().standardIcon(QStyle.SP_ArrowForward)
        self.forwardAction = QAction(icon_forward, "Forward", self)
        self.forwardAction.setShortcut(QKeySequence.Forward)
        self.forwardAction.setToolTip("Go to next state (Cmd+]")
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
        self.staleIndicatorLabel.setStyleSheet("color: orange; font-weight: bold; margin-left: 5px;")
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
        appMenu = menubar.addMenu("FileKitty")
        appMenu.addAction(self.prefAction)
        appMenu.addSeparator()
        appMenu.addAction(self.quitAction)

        # History Menu
        historyMenu = menubar.addMenu("History")
        historyMenu.addAction(self.backAction)
        historyMenu.addAction(self.forwardAction)

    def showPreferences(self):
        current_default_path = self.get_default_path()
        current_history_base_path = self.history_base_path
        dialog = PreferencesDialog(current_default_path, current_history_base_path, self)
        if dialog.exec_():
            # Read the new paths from the dialog
            # F841 Fix: Removed unused new_default_path variable
            new_history_base_path = dialog.get_history_base_path()

            # Check if history path actually changed and requires reset
            if hasattr(dialog, "history_path_changed") and dialog.history_path_changed:
                print("History path setting changed.")
                self._change_history_directory(new_history_base_path)

    def _change_history_directory(self, new_base_path: str):
        """Handles changing the history storage location."""
        old_history_dir = self.history_dir
        print(f"Changing history directory from '{old_history_dir}' based on '{new_base_path}'")

        # Stop monitoring stale status during change
        self.staleCheckTimer.stop()

        # Clean up old history *before* resetting internal state
        if old_history_dir and os.path.isdir(old_history_dir):
            print(f"Clearing history files from old directory: {old_history_dir}")
            self._cleanup_history_files(specific_dir=old_history_dir)
        else:
            print("Old history directory invalid/not set, no cleanup needed.")

        # Reset internal history state
        self.history = []
        self.history_index = -1

        # Determine and set up the new directory based on the potentially empty new_base_path
        self._determine_and_setup_history_dir()

        # Update UI reflecting the cleared history
        self._update_history_ui()

        # Restart stale checking if a valid directory was set up
        if self.history_dir:
            self.staleCheckTimer.start(STALE_CHECK_INTERVAL_MS)

        # Inform user
        QMessageBox.information(
            self,
            "History Path Changed",
            f"History location updated.\nExisting history cleared.\nNew history "
            f"stored in:\n{self.history_dir or 'Default Location (Disabled)'}",
        )

    def get_default_path(self):
        """Gets the default path for file dialogs from settings or system default."""
        settings = QSettings("Bastet", "FileKitty")
        default_docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        # Return stored path, fallback to Documents, fallback to home
        return settings.value(SETTINGS_DEFAULT_PATH_KEY, default_docs or str(Path.home()))

    def openFiles(self):
        default_path = self.get_default_path()
        options = QFileDialog.Options()
        # E501 Fix: Break long line
        file_filter = "All Files (*);;Python Files (*.py);;JavaScript Files (*.js);;TypeScript Files (*.ts *.tsx)"
        files, _ = QFileDialog.getOpenFileNames(self, "Select files", default_path, file_filter, options=options)
        if files:
            # Process selected files
            self._update_files_and_maybe_create_state(sorted(files))

    def _update_files_and_maybe_create_state(self, files: list[str]):
        """Updates the internal file list and UI, then creates a history state."""
        self.currentFiles = files
        # Reset selections when file list changes
        self.selected_items = []
        self.selection_mode = "All Files"
        self.selected_file = None

        self._update_ui_for_new_files()  # Update the QListWidget
        self.updateTextEdit()  # Update the QTextEdit content
        self._create_new_state()  # Save this new state to history

    def _update_ui_for_new_files(self):
        """Populates the file list widget based on self.currentFiles."""
        self.fileList.clear()
        has_files = bool(self.currentFiles)
        has_python_text_files = False

        for file_path in self.currentFiles:
            sanitized_path = self.sanitize_path(file_path)
            item = QListWidgetItem(sanitized_path)

            is_txt = is_text_file(file_path)
            if not is_txt:
                # Grey out and disable non-text files
                item.setForeground(QColor(Qt.gray))
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)  # Remove enabled flag
            elif file_path.endswith(".py"):
                has_python_text_files = True  # Track if selectable Python files exist

            self.fileList.addItem(item)

        # Enable "Select Classes/Functions" only if there are Python text files
        self.btnSelectClassesFunctions.setEnabled(has_python_text_files)
        self.btnRefresh.setEnabled(has_files)  # Enable refresh if there are any files

    def selectClassesFunctions(self):
        """Opens the dialog to select specific classes/functions from Python files."""
        all_classes, all_functions, parse_errors = {}, {}, []

        # Parse only the Python files that are also text files
        python_text_files = [f for f in self.currentFiles if f.endswith(".py") and is_text_file(f)]

        for file_path in python_text_files:
            try:
                classes, functions, _, _ = parse_python_file(file_path)
                all_classes[file_path], all_functions[file_path] = classes, functions
            except Exception as e:
                parse_errors.append(f"{Path(file_path).name}: {e}")

        if parse_errors:
            QMessageBox.warning(self, "Parsing Error", "Could not parse some files:\n" + "\n".join(parse_errors))

        # Check if any symbols were found across all parsable files
        if not (any(all_classes.values()) or any(all_functions.values())) and not parse_errors:
            QMessageBox.information(
                self, "No Symbols Found", "No Python classes or functions found in the selected text files."
            )
            return  # Don't show dialog if nothing to select

        # Store current state to detect changes
        old_selected_items = set(self.selected_items)
        old_mode, old_file = self.selection_mode, self.selected_file

        # Show the dialog
        dialog = SelectClassesFunctionsDialog(all_classes, all_functions, self.selected_items, self)
        if dialog.exec_():  # User clicked OK
            new_selected_items, new_mode, new_file = (
                dialog.get_selected_items(),
                dialog.get_mode(),
                dialog.get_selected_file(),
            )

            # Check if the selection state actually changed
            state_changed = (
                set(new_selected_items) != old_selected_items or new_mode != old_mode or new_file != old_file
            )

            if state_changed:
                self.selected_items, self.selection_mode, self.selected_file = new_selected_items, new_mode, new_file
                self.updateTextEdit()  # Regenerate text output
                self._create_new_state()  # Save the new state

    def copyToClipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.textEdit.toPlainText())

    def updateLineCountAndCopyButton(self):
        """Updates the line count label and enables/disables the copy button."""
        text = self.textEdit.toPlainText()
        # Count non-empty lines
        line_count = len([line for line in text.splitlines() if line.strip()]) if text else 0
        self.lineCountLabel.setText(f"Lines: {line_count}")
        self.btnCopy.setEnabled(bool(text))  # Enable copy if there is text

    def refreshText(self):
        """Reloads content from the current file list and updates the text view."""
        try:
            self.updateTextEdit()  # Re-process files
            self._create_new_state()  # Create a new history entry for the refreshed state
        except Exception as e:
            QMessageBox.warning(self, "Refresh Error", f"Failed to refresh files: {str(e)}")

    def sanitize_path(self, file_path):
        """Attempts to shorten the file path using '~' for the home directory."""
        try:
            path = Path(file_path).resolve()
            home_dir = Path.home().resolve()

            # Use is_relative_to if available (Python 3.9+)
            if hasattr(path, "is_relative_to") and path.is_relative_to(home_dir):
                return str(Path("~") / path.relative_to(home_dir))
            # Fallback for older Python or different scenarios
            elif str(path).startswith(str(home_dir)):
                # Manually replace the home directory part
                return "~" + str(path)[len(str(home_dir)) :]
            # If not relative to home, return the absolute path
            return str(path)
        except Exception:
            # In case of any error (e.g., resolving issues), return original path
            return file_path

    def updateTextEdit(self):
        """Generates the combined text output based on current files and selections."""
        if self._is_loading_state:  # Prevent updates while loading history
            return

        combined_code, files_to_process, parse_errors = "", [], []

        # Determine which files to process based on selection mode
        if self.selection_mode == "Single File" and self.selected_file:
            if self.selected_file in self.currentFiles:
                files_to_process = [self.selected_file]
            else:
                # Handle case where selected file is no longer valid
                self.textEdit.setPlainText(f"# Error: Selected file {Path(self.selected_file).name} not found.")
                self.updateLineCountAndCopyButton()
                return
        else:  # "All Files" mode
            files_to_process = self.currentFiles

        for file_path in files_to_process:
            # --- Skip non-text files ---
            if not is_text_file(file_path):
                continue  # Don't include content from non-text files

            sanitized_path = self.sanitize_path(file_path)
            try:
                # Process Python files (potentially filtering classes/functions)
                if file_path.endswith(".py"):
                    classes, functions, _, file_content = parse_python_file(file_path)
                    is_filtered = bool(self.selected_items)
                    items_in_this_file = set(classes) | set(functions)

                    # Determine if filtering applies to *this specific file*
                    relevant_items_exist = any(item in items_in_this_file for item in self.selected_items)
                    should_filter_this_file = is_filtered and (
                        self.selection_mode == "Single File"  # Always filter in single file mode if items selected
                        or relevant_items_exist  # Filter in All Files mode only if file contains selected items
                    )

                    if should_filter_this_file:
                        # Determine *which* items to extract from this file
                        items_to_extract = (
                            self.selected_items  # Extract all selected items if in single file mode
                            if self.selection_mode == "Single File"
                            else [item for item in self.selected_items if item in items_in_this_file]
                        )
                        filtered_code = extract_code_and_imports(file_content, items_to_extract, sanitized_path)

                        if filtered_code.strip():  # Add only if extraction yielded something
                            combined_code += filtered_code + "\n"
                        # If filtering yields nothing, we implicitly skip this file's content

                    else:  # Not filtering this Python file, include its whole content
                        combined_code += f"# {sanitized_path}\n\n```python\n{file_content}\n```\n\n"

                # Process other (text) file types
                else:
                    file_content = read_file_contents(file_path)
                    lang = self.detect_language(file_path)  # Get language hint for markdown
                    combined_code += f"# {sanitized_path}\n\n```{lang}\n{file_content}\n```\n\n"

            except FileNotFoundError:
                parse_errors.append(f"{sanitized_path}: File not found")
            except Exception as e:
                # Catch parsing or reading errors
                parse_errors.append(f"{sanitized_path}: {e}")

        # Update the text edit widget
        self.textEdit.setPlainText(combined_code.strip())
        self.updateLineCountAndCopyButton()  # Update status bar and copy button state

        # Show accumulated errors, if any
        if parse_errors:
            QMessageBox.warning(
                self, "Processing Errors", "Errors occurred for some files:\n" + "\n".join(parse_errors)
            )

    def detect_language(self, file_path):
        """Returns a language identifier string based on file extension for Markdown code blocks."""
        suffix = Path(file_path).suffix.lower()
        # Common language mappings
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".hpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".cs": "csharp",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".xml": "xml",
            ".md": "markdown",
            ".sh": "bash",
            ".rb": "ruby",
            ".php": "php",
            ".go": "go",
            ".rs": "rust",
            ".swift": "swift",
            ".kt": "kotlin",
            ".sql": "sql",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".ini": "ini",
            ".cfg": "ini",
            ".dockerfile": "dockerfile",
            ".tf": "terraform",
            # Add more mappings as needed
        }
        return lang_map.get(suffix, "")  # Return mapped language or empty string

    def dragEnterEvent(self, event: QDragEnterEvent):
        # Accept the drag event if it contains URLs (files or directories)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        # Handle the drop event when items are released
        if event.mimeData().hasUrls():
            files_to_add = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    path_obj = Path(local_path)

                    if path_obj.is_dir():
                        # Recursively walk the directory
                        print(f"Scanning directory: {local_path}")
                        for root, _, filenames in os.walk(local_path, followlinks=False):
                            for filename in filenames:
                                file_path = os.path.join(root, filename)
                                # Optionally add more filtering here if needed (e.g., skip hidden files)
                                if Path(file_path).is_file():  # Double check it's a file
                                    files_to_add.append(file_path)
                    elif path_obj.is_file():
                        # Add individual files
                        files_to_add.append(local_path)

            if files_to_add:
                # Remove duplicates that might arise from dropping overlapping items
                unique_files = sorted(list(set(files_to_add)))
                self._update_files_and_maybe_create_state(unique_files)
                event.acceptProposedAction()
                return  # Indicate drop was handled

        event.ignore()  # Ignore if not handled

    # --- History Management ---
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculates SHA256 hash of a file's content."""
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
            return hashlib.sha256(file_content).hexdigest()
        except FileNotFoundError:
            return HASH_MISSING_SENTINEL  # Special value for missing file
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            return HASH_ERROR_SENTINEL  # Special value for other errors

    def _create_new_state(self):
        """Saves the current application state (files, selections) to the history."""
        if self._is_loading_state or not self.history_dir:
            # Do not save state if loading history or history is disabled
            return

        # Generate file hashes *only for text files* as only they affect output
        file_hashes = {f: self._calculate_file_hash(f) for f in self.currentFiles if is_text_file(f)}

        # Create state dictionary
        state = {
            "id": str(uuid.uuid4()),  # Unique ID for this state
            "timestamp": datetime.now().isoformat(),
            "files": self.currentFiles,  # List of all files (paths)
            "selected_items": self.selected_items,  # List of selected class/function names
            "selection_mode": self.selection_mode,  # "All Files" or "Single File"
            "selected_file": self.selected_file,  # Path of the single selected file, if any
            "file_hashes": file_hashes,  # Hashes of text files at time of capture
        }

        # Create the JSON file path
        state_file_name = f"state_{state['id']}.json"
        state_file_path = os.path.join(self.history_dir, state_file_name)

        try:
            # Write state to JSON file
            # UP015: 'w' mode is necessary here, ignoring Ruff suggestion for this line.
            with open(state_file_path, "w") as f:
                json.dump(state, f, indent=2)

            # Manage history list: remove future states if branching
            if self.history_index < len(self.history) - 1:
                # Remove states after the current one
                states_to_remove = self.history[self.history_index + 1 :]
                self.history = self.history[: self.history_index + 1]
                # Delete the corresponding JSON files
                for old_state in states_to_remove:
                    old_file_path = os.path.join(self.history_dir, f"state_{old_state['id']}.json")
                    try:
                        os.remove(old_file_path)
                        print(f"Removed future state file: {old_file_path}")
                    except OSError as e:
                        print(f"Error removing old state file {old_file_path}: {e}")

            # Add new state and update index
            self.history.append(state)
            self.history_index = len(self.history) - 1

            # Update UI elements related to history (buttons, labels)
            self._update_history_ui()
            # Reset stale status display as this is a new, fresh state
            self._update_stale_status_display({})

        except Exception as e:
            QMessageBox.critical(self, "History Error", f"Could not save history state: {e}")

    def _load_state(self, state_index: int):
        """Loads a specific state from the history."""
        if not (0 <= state_index < len(self.history)):
            print("Invalid state index requested.")
            return

        self._is_loading_state = True  # Flag to prevent recursive updates
        state_to_load = self.history[state_index]
        state_file_name = f"state_{state_to_load['id']}.json"
        state_file_path = os.path.join(self.history_dir, state_file_name)

        try:
            # Load state details from the JSON file
            with open(state_file_path) as f:  # UP015: Removed "r" mode argument
                state_data = json.load(f)

            # Restore application state from loaded data
            self.currentFiles = state_data.get("files", [])
            self.selected_items = state_data.get("selected_items", [])
            self.selection_mode = state_data.get("selection_mode", "All Files")
            self.selected_file = state_data.get("selected_file", None)

            # Update UI elements to reflect the loaded state
            self._update_ui_for_new_files()
            self.updateTextEdit()

            # Update history index and related UI
            self.history_index = state_index
            self._update_history_ui()

            # Check and display the stale status for the loaded state
            stale_status = self._check_stale_status(state_data)
            self._update_stale_status_display(stale_status)

        except FileNotFoundError:
            QMessageBox.warning(self, "History Error", f"History state file not found:\n{state_file_path}")
            # Optionally remove the broken state from history list here
        except json.JSONDecodeError:
            QMessageBox.warning(self, "History Error", f"Could not parse history state file:\n{state_file_path}")
            # Optionally remove the broken state
        except Exception as e:
            QMessageBox.critical(self, "History Error", f"Error loading state: {e}")
        finally:
            self._is_loading_state = False  # Ensure flag is reset

    def go_back(self):
        """Navigates to the previous state in history."""
        if self.history_index > 0:
            self._load_state(self.history_index - 1)

    def go_forward(self):
        """Navigates to the next state in history."""
        if self.history_index < len(self.history) - 1:
            self._load_state(self.history_index + 1)

    def _update_history_ui(self):
        """Updates history-related UI elements (buttons, status label)."""
        history_count = len(self.history)
        can_go_back = self.history_index > 0
        can_go_forward = self.history_index < history_count - 1

        self.backAction.setEnabled(can_go_back)
        self.forwardAction.setEnabled(can_go_forward)

        # Update status label (using 1-based indexing for user display)
        current_pos = self.history_index + 1 if history_count > 0 else 0
        self.historyStatusLabel.setText(f"History: {current_pos} of {history_count}")

    def _check_stale_status(self, state_data: dict) -> dict:
        """Compares current file hashes against hashes stored in state_data."""
        if not state_data:
            return {}

        stale_files = {}  # {path: "modified" | "missing" | "error"}
        stored_hashes = state_data.get("file_hashes", {})
        current_text_files = state_data.get("files", [])  # Check against files in the state

        for file_path in current_text_files:
            # Only check hashes for files that were originally text files
            if file_path in stored_hashes:
                current_hash = self._calculate_file_hash(file_path)
                stored_hash = stored_hashes[file_path]

                if current_hash == HASH_MISSING_SENTINEL:
                    stale_files[file_path] = "missing"
                elif current_hash == HASH_ERROR_SENTINEL:
                    stale_files[file_path] = "error"
                elif current_hash != stored_hash:
                    stale_files[file_path] = "modified"
        return stale_files

    def _poll_stale_status(self):
        """Periodically checks if the current history state's files are stale."""
        if self._is_loading_state or not self.history or self.history_index < 0:
            return  # Don't check if loading, no history, or index invalid

        current_state_data = self.history[self.history_index]
        stale_status = self._check_stale_status(current_state_data)
        self._update_stale_status_display(stale_status)

    def _update_stale_status_display(self, stale_status: dict):
        """Updates the UI label to indicate file staleness."""
        if not stale_status:
            self.staleIndicatorLabel.hide()
            self.staleIndicatorLabel.setText("")
            self.staleIndicatorLabel.setToolTip("")
            return

        # Determine the most severe status present
        if any(v == "missing" for v in stale_status.values()):
            display_text = "Files Missing!"
        elif any(v == "error" for v in stale_status.values()):
            display_text = "File Errors!"
        elif any(v == "modified" for v in stale_status.values()):
            display_text = "Files Modified"
        else:  # Should not happen if stale_status is not empty, but handle defensively
            display_text = "Files Changed"

        # Create a tooltip listing the affected files
        tooltip_lines = ["Files have changed since this history state was captured:"]
        for path, status in stale_status.items():
            sanitized = self.sanitize_path(path)
            tooltip_lines.append(f"- {sanitized} ({status})")
        tooltip = "\n".join(tooltip_lines)

        # Update the label
        self.staleIndicatorLabel.setText(f"⚠️ {display_text}")
        self.staleIndicatorLabel.setToolTip(tooltip)
        self.staleIndicatorLabel.show()

    def _cleanup_history_files(self, specific_dir: str | None = None):
        """Removes history JSON files on exit or when directory changes."""
        cleanup_dir = specific_dir or self.history_dir
        if not cleanup_dir or not os.path.isdir(cleanup_dir):
            if not specific_dir:  # Only print if it's the regular exit cleanup
                print("History directory not set or invalid, skipping cleanup.")
            return

        print(f"Cleaning up history files in: {cleanup_dir}")
        cleaned_count = 0
        for filename in os.listdir(cleanup_dir):
            if filename.startswith("state_") and filename.endswith(".json"):
                file_path = os.path.join(cleanup_dir, filename)
                try:
                    os.remove(file_path)
                    cleaned_count += 1
                except OSError as e:
                    print(f"Error removing history file {file_path}: {e}")
        print(f"Removed {cleaned_count} history state files.")
        # Optionally remove the history directory itself if empty, but be cautious
        # try:
        #     if not os.listdir(cleanup_dir): # Check if empty
        #          os.rmdir(cleanup_dir)
        #          print(f"Removed empty history directory: {cleanup_dir}")
        # except OSError as e:
        #      print(f"Error removing history directory {cleanup_dir}: {e}")


# --- Python Parsing Logic ---
def read_file_contents(file_path):
    """Reads file content, trying common encodings."""
    encodings_to_try = ["utf-8", "latin-1", "windows-1252"]
    for encoding in encodings_to_try:
        try:
            # UP015: Remove default 'r' mode.
            with open(file_path, encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:  # UP024 Fix: Keep FileNotFoundError specific as intended
            raise
        except OSError as e:  # UP024 Fix: Catch other IO errors as OSError
            # Catch other potential read errors
            raise OSError(f"Error reading file {file_path}: {e}") from e
    # If all encodings fail
    raise UnicodeDecodeError(f"Could not decode file {file_path} with tried encodings.")


class SymbolVisitor(ast.NodeVisitor):
    def __init__(self):
        self.classes = []
        self.functions = []
        self.imports = set()
        self.imported_names = {}  # Maps alias to original name or module

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)  # Visit children (e.g., methods within class)

    def visit_FunctionDef(self, node):
        # Check if it's a top-level function (not a method inside a class)
        # This basic check assumes top-level functions aren't deeply nested
        # A more robust check might involve tracking the parent node type.
        # F841 Fix: Removed unused is_method calculation block
        # Simplified: Assume functions directly under the module root are not methods
        # This might incorrectly include functions defined inside other functions.
        # For this tool's purpose (extracting top-level definitions), it's likely sufficient.
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
            self.imported_names[alias.asname or alias.name] = alias.name

    def visit_ImportFrom(self, node):
        module_name = node.module or ""  # Handle 'from . import ...'
        base_import = f"from {'.' * node.level}{module_name} import "
        imported_items = []
        for alias in node.names:
            name = alias.name
            asname = alias.asname
            imported_items.append(f"{name}" + (f" as {asname}" if asname else ""))
            # Store mapping from the name used in the code (alias or original) to the module
            self.imported_names[asname or name] = f"{module_name}.{name}"  # Approximate source
        self.imports.add(base_import + ", ".join(imported_items))


def parse_python_file(file_path):
    """Parses a Python file and extracts classes, functions, and imports."""
    file_content = read_file_contents(file_path)
    try:
        tree = ast.parse(file_content)
        visitor = SymbolVisitor()
        visitor.visit(tree)
        return visitor.classes, visitor.functions, list(visitor.imports), file_content
    except SyntaxError as e:
        raise ValueError(f"Syntax error in {file_path}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to parse {file_path}: {e}") from e


def extract_code_and_imports(file_content, selected_items, file_path_for_header):
    """Extracts code for selected classes/functions and related imports."""
    try:
        tree = ast.parse(file_content)
    except Exception as e:
        return f"# Error parsing {file_path_for_header}: {e}\n"

    visitor = SymbolVisitor()
    visitor.visit(tree)  # First pass to get all symbols and imports

    extractor = CodeExtractor(selected_items, visitor.imported_names)
    extractor.visit(tree)

    # Add relevant imports
    relevant_imports = set()
    # Add imports directly related to the selected items (less precise, might grab too many)
    # A more sophisticated approach would track dependencies within the selected code blocks.
    # For simplicity, add all imports found in the file if any selected item exists.
    if extractor.extracted_code:
        relevant_imports.update(visitor.imports)  # Add all found imports for now

    # Format output
    output_parts = []
    output_parts.append(f"# Code from: {file_path_for_header}")
    if relevant_imports:
        output_parts.append("# Relevant Imports:")
        output_parts.extend(sorted(list(relevant_imports)))
        output_parts.append("")  # Add a blank line

    if extractor.extracted_code:
        output_parts.append("# Selected Classes/Functions:")
        output_parts.append(extractor.extracted_code.strip())
    elif selected_items:
        # Indicate if selected items were requested but none found/extracted
        output_parts.append(f"# No code found for selected items: {', '.join(selected_items)}")

    return "\n".join(output_parts) + "\n"


class CodeExtractor(ast.NodeVisitor):
    def __init__(self, selected_items, imported_names):
        self.selected_items = set(selected_items)
        self.imported_names = imported_names
        self.extracted_code = ""
        self._current_indent = 0  # Basic indentation tracking

    def _get_source_segment(self, node, file_content_lines):
        """Safely extracts source segment using ast.get_source_segment if possible."""
        try:
            # ast.get_source_segment is preferred as it handles nuances better
            return ast.get_source_segment(file_content_lines, node)
        except Exception:
            # Fallback to manual slicing if get_source_segment fails (e.g., complex f-strings)
            try:
                start_line, start_col = node.lineno - 1, node.col_offset
                end_line, end_col = node.end_lineno - 1, node.end_col_offset
                lines = file_content_lines.splitlines(True)  # Keep line endings
                if start_line == end_line:
                    return lines[start_line][start_col:end_col]
                else:
                    first_line = lines[start_line][start_col:]
                    middle_lines = lines[start_line + 1 : end_line]
                    last_line = lines[end_line][:end_col]
                    return "".join([first_line] + middle_lines + [last_line])
            except Exception as e_fallback:
                print(f"Fallback source extraction failed: {e_fallback}")
                return None  # Indicate failure

    def visit_ClassDef(self, node):
        if node.name in self.selected_items:
            try:
                # Use ast.unparse if available (Python 3.9+) for cleaner output
                if hasattr(ast, "unparse"):
                    segment = ast.unparse(node)
                else:
                    # Fallback for older Python: try getting source segment
                    # This requires the original file content accessible here
                    # For now, we'll just indicate the class was selected
                    # A better fallback would require passing file_content down
                    segment = f"# Selected Class: {node.name}\n..."
                    # segment = self._get_source_segment(node, ???) # Needs file_content

                self.extracted_code += segment + "\n\n"
            except Exception as e:
                print(f"Error extracting source for class {node.name}: {e}")
                self.extracted_code += f"# Error extracting class {node.name}\n\n"
        # Do not visit children if the class itself is selected (we take the whole block)

    def visit_FunctionDef(self, node):
        # Check if it's a top-level function (or method if needed later) and selected
        # F841 Fix: Removed unused is_likely_top_level calculation
        # F841 Fix: Removed unused is_top_level_approx calculation

        if node.name in self.selected_items:  # Simplified: extract if name matches
            try:
                if hasattr(ast, "unparse"):
                    segment = ast.unparse(node)
                else:
                    # Fallback needs file_content
                    segment = f"# Selected Function: {node.name}\n..."

                self.extracted_code += segment + "\n\n"
            except Exception as e:
                print(f"Error extracting source for function {node.name}: {e}")
                self.extracted_code += f"# Error extracting function {node.name}\n\n"
        # Do not visit children if function selected


# --- Application Entry Point ---
def main():
    app = QApplication(sys.argv)
    # Set Organization and Application Name for QSettings
    app.setOrganizationName("Bastet")
    app.setApplicationName("FileKitty")

    picker = FilePicker()
    picker.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # Add parent processing logic if needed for AST parent pointers, e.g.:
    # tree = ast.parse(file_content)
    # for node in ast.walk(tree):
    #     for child in ast.iter_child_nodes(node):
    #          child.parent = node
    # # Then pass 'tree' to visitors if they rely on .parent
    main()
