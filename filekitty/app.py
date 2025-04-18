import ast
import atexit
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Keep existing PyQt5 imports and add new ones
from PyQt5.QtCore import QMimeData, QSettings, QSize, QStandardPaths, Qt, QTimer, QUrl
from PyQt5.QtGui import (
    QColor,
    QDrag,
    QDragEnterEvent,
    QDropEvent,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QMouseEvent,
)
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
    except (OSError, FileNotFoundError):
        # Cannot read or access, treat as non-text for safety
        return False
    except Exception:
        # Catch any other unexpected errors during check
        return False


# --- Drag Out Button ---
class DragOutButton(QPushButton):
    def __init__(self, text_edit: QTextEdit, parent: QWidget | None = None):
        super().__init__("📤 Drag Out as file", parent)
        self.setToolTip("Drag this button to export as a Markdown file")
        self.text_edit = text_edit
        self._temp_file_path: str | None = None
        self.setAcceptDrops(False)  # Button itself doesn't accept drops

    def mouseMoveEvent(self, event: QMouseEvent):
        # Start drag only on left button move
        if event.buttons() != Qt.LeftButton:
            super().mouseMoveEvent(event)  # Allow normal button behavior otherwise
            return

        content = self.text_edit.toPlainText()
        if not content.strip():
            return  # Don't drag if no content

        # --- Create a temporary file ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation))
        if not temp_dir.exists():
            # Handle case where temp location might not exist (unlikely but possible)
            print("Warning: Default temporary location not found, cannot create drag file.")
            return
        temp_file = temp_dir / f"FileKitty_{timestamp}.md"

        try:
            temp_file.write_text(content, encoding="utf-8")
            self._temp_file_path = str(temp_file)

            # --- Track file for cleanup (using parent FilePicker instance) ---
            if hasattr(self.parent(), "_dragged_out_temp_files"):
                self.parent()._dragged_out_temp_files.append(self._temp_file_path)

        except OSError as e:
            print(f"Error creating temporary file for drag: {e}")
            QMessageBox.warning(self.parent(), "Drag Error", f"Could not create temporary file:\n{e}")
            return  # Abort drag if file creation fails

        # --- Prepare MIME data ---
        mime_data = QMimeData()
        # Provide the file URL for file system drops
        mime_data.setUrls([QUrl.fromLocalFile(self._temp_file_path)])
        # Provide the text content for direct text drops (e.g., into text editors)
        mime_data.setText(content)

        # --- Execute the drag operation ---
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        # Suggest CopyAction, but target application decides final action
        # Note: drag.exec_() blocks until drop is complete
        drag.exec_(Qt.CopyAction)

        # --- Cleanup attempt (optional, immediate) ---
        # We register cleanup via atexit instead for robustness
        # if self._temp_file_path:
        #     try:
        #         # os.remove(self._temp_file_path)
        #         pass # Let atexit handle it
        #     except OSError as e:
        #         print(f"Note: Could not immediately remove temp drag file {self._temp_file_path}: {e}")
        #     self._temp_file_path = None


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
        self.history_path_changed = False  # Flag to track if history path changed

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

        # Check if history path *will* change before saving settings
        self.history_path_changed = history_path != self.initial_history_base_path

        settings = QSettings("Bastet", "FileKitty")
        settings.setValue(SETTINGS_DEFAULT_PATH_KEY, self.get_default_path())
        settings.setValue(SETTINGS_HISTORY_PATH_KEY, history_path)
        super().accept()


class SelectClassesFunctionsDialog(QDialog):
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

        # Mode and File Selection Layout
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Selection Mode:"))
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(["All Files", "Single File"])
        self.mode_combo.currentTextChanged.connect(self.update_file_selection)
        mode_layout.addWidget(self.mode_combo)

        self.file_combo = QComboBox(self)
        self.file_combo.setVisible(False)  # Initially hidden
        self.file_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Allow expansion
        self.file_combo.currentTextChanged.connect(self.update_symbols)
        mode_layout.addWidget(self.file_combo)
        layout.addLayout(mode_layout)

        # List Widget for Symbols
        self.fileList = QListWidget(self)
        layout.addWidget(self.fileList)

        # OK Button
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
                self.fileList.addItem("No Python text files available")
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
                # Update symbols list based on the *now current* file in the combo
                self.update_symbols(self.file_combo.currentText())
        else:  # All Files mode
            self.populate_all_files()

    def update_symbols(self, file_name):
        # Update the list widget with classes/functions for the selected file
        self.fileList.clear()
        if not file_name:  # Handle case where combo might be empty briefly
            return
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
            self.fileList.addItem(f"File '{file_name}' not found in current list")

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
                    # Silently ignore files that cannot be parsed in "All Files" mode
                    pass

        if not has_content:
            self.fileList.addItem("No classes or functions found in Python text files")
            return

        for file_path, symbols in file_symbols.items():
            file_header = QListWidgetItem(f"File: {Path(file_path).name}")
            # Make header non-interactive (greyed out slightly, not checkable/selectable)
            file_header.setFlags(Qt.ItemIsEnabled)
            file_header.setForeground(QColor(Qt.darkGray))
            self.fileList.addItem(file_header)

            if symbols["classes"]:
                class_header = QListWidgetItem("  Classes:")
                class_header.setFlags(Qt.ItemIsEnabled)
                class_header.setForeground(QColor(Qt.darkGray))
                self.fileList.addItem(class_header)
                for cls in symbols["classes"]:
                    item = QListWidgetItem(f"    Class: {cls}")
                    item.setCheckState(Qt.Checked if cls in current_selection else Qt.Unchecked)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    self.fileList.addItem(item)

            if symbols["functions"]:
                func_header = QListWidgetItem("  Functions:")
                func_header.setFlags(Qt.ItemIsEnabled)
                func_header.setForeground(QColor(Qt.darkGray))
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
                        # Take the part after the first colon and space
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
        self.setGeometry(100, 100, 900, 700)  # Increased default width slightly
        self.setAcceptDrops(True)  # Allow dropping files onto the main window
        self.currentFiles: list[str] = []
        self.selected_items: list[str] = []
        self.selection_mode: str = "All Files"  # or "Single File"
        self.selected_file: str | None = None  # Path of the single selected file
        self.history_dir: str = ""  # Path to the history storage directory
        self.history_base_path: str = ""  # User-defined base path (or "" if default)
        self.history: list[dict] = []  # List of state dictionaries
        self.history_index: int = -1  # Current position in history
        self._is_loading_state: bool = False  # Flag to prevent updates during state load
        self._dragged_out_temp_files: list[str] = []  # Track temp files for cleanup

        self._determine_and_setup_history_dir()  # Setup history location

        self.staleCheckTimer = QTimer(self)
        self.staleCheckTimer.timeout.connect(self._poll_stale_status)
        if self.history_dir:  # Start polling only if history is enabled
            self.staleCheckTimer.start(STALE_CHECK_INTERVAL_MS)

        self.initUI()
        self.createActions()
        self.populateToolbar()
        self.createMenu()
        self._update_history_ui()  # Initialize history button states etc.

        # Register cleanup functions for application exit
        atexit.register(self._cleanup_history_files)
        atexit.register(self._cleanup_drag_out_files)

    def _determine_and_setup_history_dir(self) -> None:
        """Reads settings and sets up the history directory path."""
        settings = QSettings("Bastet", "FileKitty")
        stored_base_path = settings.value(SETTINGS_HISTORY_PATH_KEY, "")
        base_path_to_use = ""

        if stored_base_path and os.path.isdir(stored_base_path):
            base_path_to_use = stored_base_path
            self.history_base_path = stored_base_path  # Store the user path
            print(f"Using user-defined history base path: {base_path_to_use}")
        else:
            # Determine default temporary location robustly
            temp_loc = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
            if not temp_loc:
                # Fallback logic if standard temp location isn't found
                home_cache = Path.home() / ".cache"
                lib_cache = Path.home() / "Library" / "Caches"  # macOS specific
                if sys.platform == "darwin" and lib_cache.parent.exists():
                    temp_loc = str(lib_cache)
                elif home_cache.parent.exists():
                    temp_loc = str(home_cache)
                else:  # Last resort: current directory (not ideal)
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

        # --- Action Buttons Layout ---
        actionButtonLayout = QHBoxLayout()
        actionButtonLayout.setContentsMargins(5, 5, 5, 5)  # Add some padding

        btnOpen = QPushButton("📂 Select Files", self)
        btnOpen.setToolTip("Open the file selection dialog")
        btnOpen.clicked.connect(self.openFiles)
        actionButtonLayout.addWidget(btnOpen)

        self.btnSelectClassesFunctions = QPushButton("🔍 Select Code", self)  # Renamed slightly
        self.btnSelectClassesFunctions.setToolTip("Select specific classes/functions from Python files")
        self.btnSelectClassesFunctions.clicked.connect(self.selectClassesFunctions)
        self.btnSelectClassesFunctions.setEnabled(False)  # Disabled initially
        actionButtonLayout.addWidget(self.btnSelectClassesFunctions)

        self.btnRefresh = QPushButton("🔄 Refresh", self)
        self.btnRefresh.setToolTip("Reload content from the selected files")
        self.btnRefresh.clicked.connect(self.refreshText)
        self.btnRefresh.setEnabled(False)  # Disabled initially
        actionButtonLayout.addWidget(self.btnRefresh)

        self.btnCopy = QPushButton("📋 Copy", self)  # Shortened label
        self.btnCopy.setToolTip("Copy the generated text to the clipboard")
        self.btnCopy.clicked.connect(self.copyToClipboard)
        self.btnCopy.setEnabled(False)  # Disabled initially
        actionButtonLayout.addWidget(self.btnCopy)

        # --- Add the Drag Out Button ---
        self.btnDragOut = DragOutButton(self.textEdit, self)  # Pass textEdit and parent (self)
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
        current_history_base_path = self.history_base_path  # Use the stored base path
        dialog = PreferencesDialog(current_default_path, current_history_base_path, self)
        if dialog.exec_():
            # Settings are saved within the dialog's accept() method
            # Check if the history path setting actually triggered a change
            if dialog.history_path_changed:
                print("History path setting changed.")
                # The dialog now sets the flag, read the new base path from settings if needed
                new_history_base_path = dialog.get_history_base_path()
                self._change_history_directory(new_history_base_path)

    def _change_history_directory(self, new_base_path: str):
        """Handles changing the history storage location."""
        old_history_dir = self.history_dir
        print(f"Attempting to change history directory from '{old_history_dir}' based on '{new_base_path}'")

        # Stop monitoring stale status during change
        self.staleCheckTimer.stop()

        # Clean up old history *before* resetting internal state
        # Pass the specific directory to ensure the correct one is cleaned
        self._cleanup_history_files(specific_dir=old_history_dir)

        # Reset internal history state
        self.history = []
        self.history_index = -1

        # Determine and set up the new directory based on the potentially empty new_base_path
        # Re-read settings to get the potentially updated history path
        self._determine_and_setup_history_dir()

        # Update UI reflecting the cleared history
        self._update_history_ui()

        # Restart stale checking if a valid directory was set up
        if self.history_dir:
            self.staleCheckTimer.start(STALE_CHECK_INTERVAL_MS)
            QMessageBox.information(
                self,
                "History Path Changed",
                f"History location updated and existing history cleared."
                f"\nNew history will be stored in:\n{self.history_dir}",
            )
        else:
            QMessageBox.warning(
                self,
                "History Path Error",
                "History location could not be set. History feature disabled.",
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
                # Grey out and disable non-text files slightly differently
                item.setForeground(QColor(Qt.gray))
                # Keep selectable to allow removal, but indicate it's non-text
                item.setToolTip("Binary or non-standard text file, content not shown.")
                # item.setFlags(item.flags() & ~Qt.ItemIsEnabled) # Keep enabled
            elif file_path.endswith(".py"):
                has_python_text_files = True  # Track if selectable Python files exist

            self.fileList.addItem(item)

        # Enable "Select Code" only if there are Python text files
        self.btnSelectClassesFunctions.setEnabled(has_python_text_files)
        self.btnRefresh.setEnabled(has_files)  # Enable refresh if there are any files

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
                self._create_new_state()  # Save the new state

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
            self._create_new_state()  # Create a new history entry for the refreshed state
        except Exception as e:
            QMessageBox.warning(self, "Refresh Error", f"Failed to refresh files: {str(e)}")
            print(f"Refresh error details: {e}")  # Log details

    def sanitize_path(self, file_path: str) -> str:
        """Attempts to shorten the file path using '~' for the home directory."""
        try:
            path = Path(file_path).resolve()
            home_dir = Path.home().resolve()

            # Use is_relative_to if available (Python 3.9+)
            if hasattr(path, "is_relative_to") and path.is_relative_to(home_dir):
                return str(Path("~") / path.relative_to(home_dir))
            # Fallback for older Python or different drive letters on Windows
            # Convert both to strings for reliable comparison across OS/versions
            str_path = str(path)
            str_home = str(home_dir)
            if str_path.startswith(str_home):
                # Ensure a path separator follows the home dir part before replacing
                if len(str_path) > len(str_home) and str_path[len(str_home)] in (os.sep, os.altsep):
                    return "~" + str_path[len(str_home) :]
                elif len(str_path) == len(str_home):  # Exact match to home dir
                    return "~"
            # If not relative to home, return the absolute path
            return str(path)
        except Exception as e:
            # In case of any error (e.g., resolving issues), return original path
            print(f"Warning: Could not sanitize path '{file_path}': {e}")
            return file_path

    def updateTextEdit(self):
        """Generates the combined text output based on current files and selections."""
        if self._is_loading_state:  # Prevent updates while loading history
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

            sanitized_path = self.sanitize_path(file_path)
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
                            filtered_code = extract_code_and_imports(file_content, items_to_extract, sanitized_path)
                            if filtered_code.strip():  # Add only if extraction yielded something
                                combined_code += filtered_code + "\n\n"  # Add extra newline between extracts
                        # If filtering yields nothing for this file, we implicitly skip its content

                    else:  # Not filtering this Python file, include its whole content
                        combined_code += f"# {sanitized_path}\n\n```python\n{file_content.strip()}\n```\n\n"

                # Process other (text) file types
                else:
                    file_content = read_file_contents(file_path)
                    lang = self.detect_language(file_path)  # Get language hint for markdown
                    combined_code += f"# {sanitized_path}\n\n```{lang}\n{file_content.strip()}\n```\n\n"

            except FileNotFoundError:
                parse_errors.append(f"{sanitized_path}: File not found")
            except Exception as e:
                # Catch parsing or reading errors
                parse_errors.append(f"{sanitized_path}: Error processing - {e}")

        # Update the text edit widget
        self.textEdit.setPlainText(combined_code.strip())
        # updateLineCountAndActionButtons is called automatically via textChanged signal

        # Show accumulated errors, if any
        if parse_errors:
            QMessageBox.warning(
                self, "Processing Errors", "Errors occurred for some files:\n" + "\n".join(parse_errors)
            )

    def detect_language(self, file_path: str) -> str:
        """Returns a language identifier string based on file extension for Markdown code blocks."""
        suffix = Path(file_path).suffix.lower()
        # Common language mappings (expand as needed)
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
            ".log": "log",
            ".txt": "",  # Default to no language for .txt
        }
        return lang_map.get(suffix, "")  # Return mapped language or empty string

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
            print(f"Drop event with {len(dropped_urls)} URLs detected.")  # Debug print

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
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculates SHA256 hash of a file's content."""
        try:
            # Read in chunks to handle potentially large files without huge memory use
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                while chunk := f.read(4096):  # Read in 4KB chunks
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            return HASH_MISSING_SENTINEL  # Special value for missing file
        except PermissionError:
            print(f"Permission error hashing file {file_path}")
            return HASH_ERROR_SENTINEL
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            return HASH_ERROR_SENTINEL  # Special value for other errors

    def _create_new_state(self):
        """Saves the current application state (files, selections) to the history."""
        if self._is_loading_state or not self.history_dir:
            # Do not save state if loading history or history is disabled
            return

        # Generate file hashes *only for text files* as only they affect output/stale check
        # Use currentFiles list which contains all files added by user
        current_text_files = [f for f in self.currentFiles if is_text_file(f)]
        file_hashes = {f: self._calculate_file_hash(f) for f in current_text_files}

        # Create state dictionary
        state = {
            "id": str(uuid.uuid4()),  # Unique ID for this state
            "timestamp": datetime.now().isoformat(),
            "files": self.currentFiles,  # List of all files (paths) added by user
            "selected_items": self.selected_items,  # List of selected class/function names
            "selection_mode": self.selection_mode,  # "All Files" or "Single File"
            "selected_file": self.selected_file,  # Path of the single selected file, if any
            "file_hashes": file_hashes,  # Hashes of *text* files at time of capture
        }

        # --- Avoid saving duplicate states ---
        if self.history_index >= 0:
            last_state = self.history[self.history_index]
            # Compare relevant parts of the state (excluding timestamp and ID)
            keys_to_compare = ["files", "selected_items", "selection_mode", "selected_file", "file_hashes"]
            is_duplicate = all(state.get(k) == last_state.get(k) for k in keys_to_compare)
            if is_duplicate:
                print("Skipping save, state identical to previous.")
                return  # Don't save if nothing changed

        # Create the JSON file path
        state_file_name = f"state_{state['id']}.json"
        state_file_path = os.path.join(self.history_dir, state_file_name)

        try:
            # Write state to JSON file
            with open(state_file_path, "w", encoding="utf-8") as f:
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
                        # print(f"Removed future state file: {old_file_path}") # Optional: verbose logging
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
            print(f"Invalid state index requested: {state_index} (History size: {len(self.history)})")
            return

        self._is_loading_state = True  # Flag to prevent recursive updates
        state_to_load = self.history[state_index]
        state_file_name = f"state_{state_to_load['id']}.json"
        state_file_path = os.path.join(self.history_dir, state_file_name)

        try:
            print(f"Loading state {state_index + 1} from {state_file_path}")
            # Load state details from the JSON file
            with open(state_file_path, encoding="utf-8") as f:
                state_data = json.load(f)

            # Restore application state from loaded data
            self.currentFiles = state_data.get("files", [])
            self.selected_items = state_data.get("selected_items", [])
            self.selection_mode = state_data.get("selection_mode", "All Files")
            self.selected_file = state_data.get("selected_file", None)

            # Update UI elements to reflect the loaded state
            self._update_ui_for_new_files()  # Update file list first
            self.updateTextEdit()  # Then update text edit (might depend on file list)

            # Update history index and related UI
            self.history_index = state_index
            self._update_history_ui()

            # Check and display the stale status for the loaded state
            stale_status = self._check_stale_status(state_data)
            self._update_stale_status_display(stale_status)

        except FileNotFoundError:
            QMessageBox.warning(self, "History Error", f"History state file not found:\n{state_file_path}")
            # Optionally remove the broken state from history list here
            del self.history[state_index]
            # Adjust index carefully if removing current/previous states
            self.history_index = min(self.history_index, len(self.history) - 1)
            self._update_history_ui()  # Update UI after removal
        except json.JSONDecodeError:
            QMessageBox.warning(self, "History Error", f"Could not parse history state file:\n{state_file_path}")
            # Optionally remove the broken state
            del self.history[state_index]
            self.history_index = min(self.history_index, len(self.history) - 1)
            self._update_history_ui()
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
        # Check against the list of files *that were text files* when the state was saved
        # These are the keys in stored_hashes
        files_to_check = list(stored_hashes.keys())

        for file_path in files_to_check:
            current_hash = self._calculate_file_hash(file_path)
            stored_hash = stored_hashes[file_path]  # We know this exists

            if current_hash == HASH_MISSING_SENTINEL:
                stale_files[file_path] = "missing"
            elif current_hash == HASH_ERROR_SENTINEL:
                stale_files[file_path] = "error"
            elif current_hash != stored_hash:
                stale_files[file_path] = "modified"
            # If hash matches, file is not stale, do nothing
        return stale_files

    def _poll_stale_status(self):
        """Periodically checks if the current history state's files are stale."""
        # Don't check if loading, history disabled, or no valid state selected
        if self._is_loading_state or not self.history_dir or not self.history or self.history_index < 0:
            # Ensure label is hidden if checks are disabled
            if self.staleIndicatorLabel.isVisible():
                self._update_stale_status_display({})
            return

        # Check only if there's a valid state selected
        if 0 <= self.history_index < len(self.history):
            current_state_data = self.history[self.history_index]
            stale_status = self._check_stale_status(current_state_data)
            self._update_stale_status_display(stale_status)
        else:
            # If index is somehow invalid, ensure label is hidden
            self._update_stale_status_display({})

    def _update_stale_status_display(self, stale_status: dict):
        """Updates the UI label to indicate file staleness."""
        if not stale_status:
            self.staleIndicatorLabel.hide()
            self.staleIndicatorLabel.setText("")
            self.staleIndicatorLabel.setToolTip("")
            return

        # Determine the most severe status present for concise display text
        statuses = stale_status.values()
        if "missing" in statuses:
            display_text = "Files Missing!"
        elif "error" in statuses:
            display_text = "File Errors!"
        elif "modified" in statuses:
            display_text = "Files Modified"
        else:  # Should not happen if stale_status is not empty
            display_text = "Files Changed (?)"

        # Create a tooltip listing the affected files
        tooltip_lines = ["Files have changed since this history state was captured:"]
        # Sort for consistent tooltip order
        for path in sorted(stale_status.keys()):
            status = stale_status[path]
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
        # Check if the directory path is valid and exists
        if not cleanup_dir or not os.path.isdir(cleanup_dir):
            if not specific_dir:  # Only print if it's the regular exit cleanup and dir was invalid
                print("History directory not set or invalid, skipping history file cleanup.")
            return

        print(f"Cleaning up history files in: {cleanup_dir}")
        cleaned_count = 0
        error_count = 0
        try:
            for filename in os.listdir(cleanup_dir):
                if filename.startswith("state_") and filename.endswith(".json"):
                    file_path = os.path.join(cleanup_dir, filename)
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except OSError as e:
                        print(f"Error removing history file {file_path}: {e}")
                        error_count += 1
            print(f"Removed {cleaned_count} history state files.")
            if error_count:
                print(f"Failed to remove {error_count} history files.")
            # Optional: Remove the directory itself if it's now empty AND it was the application's specific dir
            if not specific_dir and cleanup_dir.endswith(HISTORY_DIR_NAME):  # Safety check
                try:
                    if not os.listdir(cleanup_dir):  # Check if empty
                        os.rmdir(cleanup_dir)
                        print(f"Removed empty history directory: {cleanup_dir}")
                except OSError as e:
                    print(f"Could not remove history directory {cleanup_dir}: {e}")
        except Exception as e:
            print(f"An error occurred during history cleanup in {cleanup_dir}: {e}")

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


# --- Python Parsing Logic ---
def read_file_contents(file_path):
    """Reads file content, trying common encodings."""
    # Prioritize UTF-8, then try others common on different platforms
    encodings_to_try = ["utf-8", "latin-1", "windows-1252"]
    for encoding in encodings_to_try:
        try:
            with open(file_path, encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue  # Try next encoding
        except FileNotFoundError:
            raise  # Re-raise FileNotFoundError immediately
        except Exception as e:
            # Catch other potential read errors (permissions, etc.)
            raise OSError(f"Error reading file {file_path} with {encoding}: {e}") from e
    # If all encodings fail
    raise UnicodeDecodeError(f"Could not decode file {file_path} with tried encodings: {', '.join(encodings_to_try)}.")


class SymbolVisitor(ast.NodeVisitor):
    """Visits AST nodes to find top-level classes, functions, and all imports."""

    def __init__(self):
        self.classes = []
        self.functions = []
        self.imports = set()
        # Stores mapping of imported name (as used in code) to its origin (module or module.name)
        self.imported_names = {}

    def visit_ClassDef(self, node):
        # Assume classes defined directly under the module root are top-level
        # A more complex check could involve tracking parent node types if needed.
        self.classes.append(node.name)
        # Do not visit children here if we only want top-level class names
        # self.generic_visit(node) # Uncomment to visit methods etc. inside classes

    def visit_FunctionDef(self, node):
        # Basic check: Assume functions defined directly under the module root are top-level.
        # This might incorrectly include functions defined inside other top-level functions.
        # For the purpose of extracting major code blocks, this is often sufficient.
        # A robust check requires parent tracking (ast does not provide this by default).
        self.functions.append(node.name)
        # Do not visit children here if we only want top-level function names
        # self.generic_visit(node)

    def visit_Import(self, node):
        # Handles 'import module' and 'import module as alias'
        for alias in node.names:
            imported_name = alias.name
            alias_name = alias.asname or imported_name  # Name used in code
            self.imports.add(ast.unparse(node).strip())  # Use unparse for accurate representation
            self.imported_names[alias_name] = imported_name  # Map alias/name to module name

    def visit_ImportFrom(self, node):
        # Handles 'from module import name' and 'from module import name as alias'
        module_name = node.module or ""  # Handle 'from . import ...'
        # Use unparse for accurate representation of the import statement
        self.imports.add(ast.unparse(node).strip())
        # Map the imported names/aliases to their approximate origin
        for alias in node.names:
            original_name = alias.name
            alias_name = alias.asname or original_name  # Name used in code
            # Approximate origin: module.name (might be relative)
            full_origin = f"{'.' * node.level}{module_name}.{original_name}"
            self.imported_names[alias_name] = full_origin


def parse_python_file(file_path):
    """Parses a Python file and extracts top-level classes, functions, imports, and content."""
    file_content = read_file_contents(file_path)  # Can raise IOError or UnicodeDecodeError
    try:
        # Add type comments ignores for compatibility if needed (requires specific Python versions)
        tree = ast.parse(file_content)  # , type_comments=True)
        visitor = SymbolVisitor()
        visitor.visit(tree)
        # Return names, names, unique import strings, and the original content
        return visitor.classes, visitor.functions, sorted(list(visitor.imports)), file_content
    except SyntaxError as e:
        raise ValueError(f"Syntax error in {Path(file_path).name}: line {e.lineno} - {e.msg}") from e
    except Exception as e:
        # Catch other potential AST parsing errors
        raise RuntimeError(f"Failed to parse Python file {Path(file_path).name}: {e}") from e


def extract_code_and_imports(file_content: str, selected_items: list[str], file_path_for_header: str) -> str:
    """
    Extracts code for selected top-level classes/functions and relevant imports.
    Uses ast.unparse if possible for cleaner extraction.
    """
    try:
        # Parse the whole file to build the AST
        tree = ast.parse(file_content)
    except Exception as e:
        return f"# Error parsing {file_path_for_header} for extraction: {e}\n"

    # --- First Pass: Get all imports using SymbolVisitor ---
    import_visitor = SymbolVisitor()
    import_visitor.visit(tree)
    all_imports_in_file = sorted(list(import_visitor.imports))

    # --- Second Pass: Extract selected code blocks using CodeExtractor ---
    # Pass selected item names and the original file content (needed for fallback extraction)
    extractor = CodeExtractor(selected_items, file_content)
    extractor.visit(tree)

    # --- Determine Relevant Imports (Simple Approach) ---
    # Currently includes ALL imports from the file if any selected code was extracted.
    # A more sophisticated approach would analyze dependencies within the extracted code.
    relevant_imports = set()
    if extractor.extracted_code.strip():
        relevant_imports.update(all_imports_in_file)

    # --- Format Output ---
    output_parts = [f"# Code from: {file_path_for_header}"]
    if relevant_imports:
        output_parts.append("\n# Imports (potentially includes more than needed):")
        output_parts.extend(sorted(list(relevant_imports)))
        output_parts.append("")  # Add a blank line

    if extractor.extracted_code.strip():
        output_parts.append("# Selected Classes/Functions:")
        output_parts.append(extractor.extracted_code.strip())
    elif selected_items:
        # Indicate if selected items were requested but none found/extracted
        output_parts.append(f"# No code found for selected items: {', '.join(selected_items)}")

    # Ensure a single newline at the end
    return "\n".join(output_parts).strip() + "\n"


class CodeExtractor(ast.NodeVisitor):
    """Extracts the source code segments for selected top-level classes and functions."""

    def __init__(self, selected_items: list[str], file_content: str):
        self.selected_items = set(selected_items)
        self.extracted_code = ""
        self.file_content_lines = file_content.splitlines(True)  # Keep line endings for segment extraction

    def _get_source_segment_fallback(self, node):
        """Manually extracts source segment using line/column numbers as fallback."""
        try:
            start_line, start_col = node.lineno - 1, node.col_offset
            end_line, end_col = node.end_lineno - 1, node.end_col_offset

            if start_line == end_line:
                # Single line segment
                return self.file_content_lines[start_line][start_col:end_col]
            else:
                # Multi-line segment
                first_line = self.file_content_lines[start_line][start_col:]
                middle_lines = self.file_content_lines[start_line + 1 : end_line]
                last_line = self.file_content_lines[end_line][:end_col]
                # Ensure consistent newline endings
                code_lines = (
                    [first_line.rstrip("\r\n")]
                    + [line.rstrip("\r\n") for line in middle_lines]
                    + [last_line.rstrip("\r\n")]
                )
                return "\n".join(code_lines)
        except IndexError:
            print(f"Fallback source extraction failed for node at line {node.lineno}: Index out of range.")
            return None  # Indicate failure
        except Exception as e_fallback:
            print(f"Fallback source extraction failed for node at line {node.lineno}: {e_fallback}")
            return None  # Indicate failure

    def visit_ClassDef(self, node):
        # Extract only if the class name is in the selected set
        if node.name in self.selected_items:
            segment = None
            try:
                # Use ast.unparse if available (Python 3.9+) - generally more reliable
                if hasattr(ast, "unparse"):
                    segment = ast.unparse(node)
                else:
                    # Fallback to get_source_segment (requires ast and source content)
                    if hasattr(ast, "get_source_segment"):
                        segment = ast.get_source_segment(self.file_content_lines, node, padded=True)
                    # If that fails, try manual slicing
                    if segment is None:
                        segment = self._get_source_segment_fallback(node)

                if segment is not None:
                    self.extracted_code += segment.strip() + "\n\n"  # Add spacing between blocks
                else:
                    # If extraction failed completely
                    self.extracted_code += f"# Error: Could not extract source for class {node.name}\n\n"

            except Exception as e:
                print(f"Error processing class {node.name} during extraction: {e}")
                self.extracted_code += f"# Error extracting class {node.name}: {e}\n\n"
        # Do not visit children of the class if the whole class is selected
        # else:
        #     self.generic_visit(node) # Visit children only if class itself is not selected

    def visit_FunctionDef(self, node):
        # Extract only if the function name is in the selected set
        # Assuming we only want top-level functions for now (simplification)
        if node.name in self.selected_items:
            segment = None
            try:
                if hasattr(ast, "unparse"):
                    segment = ast.unparse(node)
                else:
                    if hasattr(ast, "get_source_segment"):
                        segment = ast.get_source_segment(self.file_content_lines, node, padded=True)
                    if segment is None:
                        segment = self._get_source_segment_fallback(node)

                if segment is not None:
                    self.extracted_code += segment.strip() + "\n\n"
                else:
                    self.extracted_code += f"# Error: Could not extract source for function {node.name}\n\n"

            except Exception as e:
                print(f"Error processing function {node.name} during extraction: {e}")
                self.extracted_code += f"# Error extracting function {node.name}: {e}\n\n"
        # Do not visit children of the function if the whole function is selected
        # else:
        #     self.generic_visit(node)


# --- Application Entry Point ---
def main():
    # Enable High DPI scaling for better visuals on modern displays
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    # Set Organization and Application Name for QSettings
    app.setOrganizationName("Bastet")
    app.setApplicationName("FileKitty")

    # Apply a style if desired (optional)
    # app.setStyle("Fusion")

    picker = FilePicker()
    picker.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # Future: Add AST parent processing here if needed for more complex analysis
    # e.g., tree = ast.parse(...) then walk and add parent pointers
    main()
