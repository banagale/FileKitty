# /code/open-source/FileKitty/filekitty/app.py
# Imports (cleaned and alphabetized where practical)
import ast
import atexit
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Keep existing PyQt5 imports
from PyQt5.QtCore import QSettings, QSize, QStandardPaths, Qt, QTimer
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QGuiApplication, QIcon, QKeySequence
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
        self.parent = parent
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
        self.file_combo.setVisible(False)
        self.file_combo.currentTextChanged.connect(self.update_symbols)
        mode_layout.addWidget(self.file_combo)
        self.fileList = QListWidget(self)
        layout.addWidget(self.fileList)
        self.btnOk = QPushButton("OK", self)
        self.btnOk.clicked.connect(self.accept)
        layout.addWidget(self.btnOk)
        self.setLayout(layout)
        initial_mode = self.parent.selection_mode if self.parent else "All Files"
        self.mode_combo.setCurrentText(initial_mode)
        self.update_file_selection(initial_mode)
        if initial_mode == "Single File" and self.parent and self.parent.selected_file:
            file_name = Path(self.parent.selected_file).name
            if self.file_combo.findText(file_name) != -1:
                self.file_combo.setCurrentText(file_name)

    def update_file_selection(self, mode):
        self.file_combo.setVisible(mode == "Single File")
        self.file_combo.clear()
        if mode == "Single File":
            python_files = [f for f in self.parent.currentFiles if f.endswith(".py")]
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
                if found_match and current_selection_name:
                    self.file_combo.setCurrentText(current_selection_name)
                elif python_files:
                    self.file_combo.setCurrentIndex(0)
                    self.update_symbols(self.file_combo.currentText())
        else:
            self.populate_all_files()

    def update_symbols(self, file_name):
        self.fileList.clear()
        selected_file = next((f for f in self.parent.currentFiles if Path(f).name == file_name), None)
        if selected_file:
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
        elif file_name:
            self.fileList.addItem(f"File '{file_name}' not found")

    def populate_all_files(self):
        self.fileList.clear()
        has_content = False
        current_selection = self.selected_items
        file_symbols = {}
        for file_path in self.parent.currentFiles:
            if file_path.endswith(".py"):
                try:
                    classes, functions, _, _ = parse_python_file(file_path)
                    if classes or functions:
                        file_symbols[file_path] = {"classes": classes, "functions": functions}
                        has_content = True
                except Exception:
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
                class_header.setFlags(file_header.flags())
                self.fileList.addItem(class_header)
                for cls in symbols["classes"]:
                    item = QListWidgetItem(f"    Class: {cls}")
                    item.setCheckState(Qt.Checked if cls in current_selection else Qt.Unchecked)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    self.fileList.addItem(item)
            if symbols["functions"]:
                func_header = QListWidgetItem("  Functions:")
                func_header.setFlags(file_header.flags())
                self.fileList.addItem(func_header)
                for func in symbols["functions"]:
                    item = QListWidgetItem(f"    Function: {func}")
                    item.setCheckState(Qt.Checked if func in current_selection else Qt.Unchecked)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    self.fileList.addItem(item)

    def accept(self):
        self.selected_items = []
        for i in range(self.fileList.count()):
            item = self.fileList.item(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                if item.checkState() == Qt.Checked:
                    text_content = item.text().strip()
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
                home_cache = Path.home() / ".cache"
                lib_cache = Path.home() / "Library" / "Caches"
                if sys.platform == "darwin" and lib_cache.parent.exists():
                    temp_loc = lib_cache
                elif home_cache.parent.exists():
                    temp_loc = home_cache
                else:
                    temp_loc = Path(".")
            base_path_to_use = str(temp_loc)
            self.history_base_path = ""
            print(f"Using default history base path: {base_path_to_use}")
        history_path = Path(base_path_to_use) / HISTORY_DIR_NAME
        try:
            history_path.mkdir(parents=True, exist_ok=True)
            self.history_dir = str(history_path)
            print(f"History directory set to: {self.history_dir}")
        except OSError as e:
            QMessageBox.critical(self, "History Error", f"Could not create history directory:\n{history_path}\n{e}")
            self.history_dir = ""

    def _setup_history_dir(self):
        pass  # Replaced by _determine_and_setup_history_dir

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.toolbar = QToolBar("History Toolbar")
        self.toolbar.setIconSize(QSize(22, 22))
        self.mainLayout.addWidget(self.toolbar)
        centralWidget = QWidget()
        centralLayout = QVBoxLayout(centralWidget)
        self.mainLayout.addWidget(centralWidget, 1)
        self.fileList = QListWidget(self)
        centralLayout.addWidget(self.fileList)
        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setFontFamily("monospace")
        centralLayout.addWidget(self.textEdit, 1)
        actionButtonLayout = QHBoxLayout()
        btnOpen = QPushButton("📂 Select Files", self)
        btnOpen.clicked.connect(self.openFiles)
        actionButtonLayout.addWidget(btnOpen)
        self.btnSelectClassesFunctions = QPushButton("🔍 Select Classes/Functions", self)
        self.btnSelectClassesFunctions.clicked.connect(self.selectClassesFunctions)
        self.btnSelectClassesFunctions.setEnabled(False)
        actionButtonLayout.addWidget(self.btnSelectClassesFunctions)
        self.btnRefresh = QPushButton("🔄 Refresh", self)
        self.btnRefresh.clicked.connect(self.refreshText)
        self.btnRefresh.setEnabled(False)
        actionButtonLayout.addWidget(self.btnRefresh)
        self.btnCopy = QPushButton("📋 Copy to Clipboard", self)
        self.btnCopy.clicked.connect(self.copyToClipboard)
        self.btnCopy.setEnabled(False)
        actionButtonLayout.addWidget(self.btnCopy)
        self.mainLayout.addLayout(actionButtonLayout)
        statusBarLayout = QHBoxLayout()
        statusBarLayout.setContentsMargins(5, 2, 5, 2)
        self.lineCountLabel = QLabel("Lines: 0")
        statusBarLayout.addWidget(self.lineCountLabel)
        self.mainLayout.addLayout(statusBarLayout)
        self.textEdit.textChanged.connect(self.updateLineCountAndCopyButton)
        self.setLayout(self.mainLayout)

    def createActions(self):
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
        self.historyStatusLabel.setContentsMargins(5, 0, 5, 0)
        self.toolbar.addWidget(self.historyStatusLabel)
        self.staleIndicatorLabel = QLabel("")
        self.staleIndicatorLabel.setToolTip(
            "Indicates if file contents have changed, are missing, or had errors since capture"
        )
        self.staleIndicatorLabel.setStyleSheet("color: orange; font-weight: bold; margin-left: 5px;")
        self.toolbar.addWidget(self.staleIndicatorLabel)
        self.staleIndicatorLabel.hide()
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

    def createMenu(self):
        menubar = QMenuBar(self)
        self.mainLayout.setMenuBar(menubar)
        appMenu = menubar.addMenu("FileKitty")
        appMenu.addAction(self.prefAction)
        appMenu.addSeparator()
        appMenu.addAction(self.quitAction)
        historyMenu = menubar.addMenu("History")
        historyMenu.addAction(self.backAction)
        historyMenu.addAction(self.forwardAction)

    def showPreferences(self):
        current_default_path = self.get_default_path()
        current_history_base_path = self.history_base_path
        dialog = PreferencesDialog(current_default_path, current_history_base_path, self)
        if dialog.exec_():
            # F841 Fix: Removed unused new_default_path variable
            new_history_base_path = dialog.get_history_base_path()
            if hasattr(dialog, "history_path_changed") and dialog.history_path_changed:
                print("History path setting changed.")
                self._change_history_directory(new_history_base_path)

    def _change_history_directory(self, new_base_path: str):
        old_history_dir = self.history_dir
        print(f"Changing history directory from '{old_history_dir}' based on '{new_base_path}'")
        self.staleCheckTimer.stop()
        if old_history_dir and os.path.isdir(old_history_dir):
            print(f"Clearing history files from old directory: {old_history_dir}")
            self._cleanup_history_files(specific_dir=old_history_dir)
        else:
            print("Old history directory invalid/not set, no cleanup.")
        self.history = []
        self.history_index = -1
        self._determine_and_setup_history_dir()
        self._update_history_ui()
        if self.history_dir:
            self.staleCheckTimer.start(STALE_CHECK_INTERVAL_MS)
        QMessageBox.information(
            self,
            "History Path Changed",
            f"History location updated.\nExisting history cleared.\nNew history stored in:\n{self.history_dir}",
        )

    def get_default_path(self):
        settings = QSettings("Bastet", "FileKitty")
        default_docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        return settings.value(SETTINGS_DEFAULT_PATH_KEY, default_docs or str(Path.home()))

    def openFiles(self):
        default_path = self.get_default_path() or str(Path.home())
        options = QFileDialog.Options()
        file_filter = "All Files (*);;Python Files (*.py);;JavaScript Files (*.js);;TypeScript Files (*.ts *.tsx)"
        files, _ = QFileDialog.getOpenFileNames(self, "Select files", default_path, file_filter, options=options)
        if files:
            self._update_files_and_maybe_create_state(sorted(files))

    def _update_files_and_maybe_create_state(self, files: list[str]):
        self.currentFiles = files
        self.selected_items = []
        self.selection_mode = "All Files"
        self.selected_file = None
        self._update_ui_for_new_files()
        self.updateTextEdit()
        self._create_new_state()

    def _update_ui_for_new_files(self):
        self.fileList.clear()
        is_python_only = bool(self.currentFiles) and all(f.endswith(".py") for f in self.currentFiles)
        has_files = bool(self.currentFiles)
        for file in self.currentFiles:
            sanitized_path = self.sanitize_path(file)
            self.fileList.addItem(sanitized_path)
        self.btnSelectClassesFunctions.setEnabled(is_python_only)
        self.btnRefresh.setEnabled(has_files)

    def selectClassesFunctions(self):
        all_classes, all_functions, parse_errors = {}, {}, []
        for file_path in self.currentFiles:
            if file_path.endswith(".py"):
                try:
                    classes, functions, _, _ = parse_python_file(file_path)
                    all_classes[file_path], all_functions[file_path] = classes, functions
                except Exception as e:
                    parse_errors.append(f"{Path(file_path).name}: {e}")
        if parse_errors:
            QMessageBox.warning(self, "Parsing Error", "Could not parse some files:\n" + "\n".join(parse_errors))
        if not (any(all_classes.values()) or any(all_functions.values())) and not parse_errors:
            QMessageBox.information(self, "No Symbols Found", "No Python classes or functions found.")
            return
        old_selected_items = set(self.selected_items)
        old_mode, old_file = self.selection_mode, self.selected_file
        dialog = SelectClassesFunctionsDialog(all_classes, all_functions, self.selected_items, self)
        if dialog.exec_():
            new_selected_items, new_mode, new_file = (
                dialog.get_selected_items(),
                dialog.get_mode(),
                dialog.get_selected_file(),
            )
            state_changed = (
                set(new_selected_items) != old_selected_items or new_mode != old_mode or new_file != old_file
            )
            if state_changed:
                self.selected_items, self.selection_mode, self.selected_file = new_selected_items, new_mode, new_file
                self.updateTextEdit()
                self._create_new_state()

    def copyToClipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.textEdit.toPlainText())

    def updateLineCountAndCopyButton(self):
        text = self.textEdit.toPlainText()
        line_count = len([line for line in text.splitlines() if line.strip()]) if text else 0
        self.lineCountLabel.setText(f"Lines: {line_count}")
        self.btnCopy.setEnabled(bool(text))

    def refreshText(self):
        try:
            self.updateTextEdit()
            self._create_new_state()
        except Exception as e:
            QMessageBox.warning(self, "Refresh Error", f"Failed to refresh files: {str(e)}")

    def sanitize_path(self, file_path):
        try:
            path = Path(file_path).resolve()
            home_dir = Path.home().resolve()
            if hasattr(path, "is_relative_to") and path.is_relative_to(home_dir):
                return str(Path("~") / path.relative_to(home_dir))
            elif str(path).startswith(str(home_dir)):
                return "~" + str(path)[len(str(home_dir)) :]
            return str(path)
        except Exception:
            return file_path

    def updateTextEdit(self):
        if self._is_loading_state:
            return
        combined_code, files_to_process, parse_errors = "", [], []
        if self.selection_mode == "Single File" and self.selected_file:
            if self.selected_file in self.currentFiles:
                files_to_process = [self.selected_file]
            else:
                self.textEdit.setPlainText(f"# Error: Selected file {Path(self.selected_file).name} not found.")
                self.updateLineCountAndCopyButton()
                return
        else:
            files_to_process = self.currentFiles
        for file_path in files_to_process:
            sanitized_path = self.sanitize_path(file_path)
            try:
                if file_path.endswith(".py"):
                    classes, functions, _, file_content = parse_python_file(file_path)
                    is_filtered = bool(self.selected_items)
                    items_in_this_file = set(classes) | set(functions)
                    relevant_items_exist = any(item in items_in_this_file for item in self.selected_items)
                    should_filter_this_file = is_filtered and (
                        self.selection_mode == "Single File" or relevant_items_exist
                    )
                    if should_filter_this_file:
                        items = (
                            self.selected_items
                            if self.selection_mode == "Single File"
                            else [item for item in self.selected_items if item in items_in_this_file]
                        )
                        filtered_code = extract_code_and_imports(file_content, items, sanitized_path)

                        if filtered_code.strip():
                            combined_code += filtered_code + "\n"
                    else:
                        combined_code += f"# {sanitized_path}\n\n```python\n{file_content}\n```\n\n"
                else:
                    file_content = read_file_contents(file_path)
                    lang = self.detect_language(file_path)
                    combined_code += f"# {sanitized_path}\n\n```{lang}\n{file_content}\n```\n\n"
            except FileNotFoundError:
                parse_errors.append(f"{sanitized_path}: File not found")
            except Exception as e:
                parse_errors.append(f"{sanitized_path}: {e}")
        self.textEdit.setPlainText(combined_code.strip())
        self.updateLineCountAndCopyButton()
        if parse_errors:
            QMessageBox.warning(
                self, "Processing Errors", "Errors occurred for some files:\n" + "\n".join(parse_errors)
            )

    def detect_language(self, file_path):
        suffix = Path(file_path).suffix.lower()
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
        }
        return lang_map.get(suffix, "")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile()

                    if Path(local_path).is_file():
                        files.append(local_path)
            if files:
                self._update_files_and_maybe_create_state(sorted(files))
                event.acceptProposedAction()
                return
        event.ignore()

    # --- History Management ---
    def _calculate_file_hash(self, file_path: str) -> str:
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
            return hashlib.sha256(file_content).hexdigest()
        except FileNotFoundError:
            return HASH_MISSING_SENTINEL
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            return HASH_ERROR_SENTINEL

    def _create_new_state(self):
        if self._is_loading_state or not self.history_dir:
            return
        current_files, current_text = list(self.currentFiles), self.textEdit.toPlainText()
        current_selected_items, current_mode = list(self.selected_items), self.selection_mode
        current_sel_file = self.selected_file
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content_hashes = {}
        for f_path in current_files:
            try:
                check_path = str(Path(f_path).resolve())
            except Exception:
                check_path = f_path
            content_hashes[f_path] = self._calculate_file_hash(check_path)
        if self.history_index >= 0:
            last_state_path = self.history[self.history_index]["path"]
            try:
                with open(last_state_path, encoding="utf-8") as f:
                    last_state_data = json.load(f)

                if current_text == last_state_data.get("text_content", ""):
                    return
            except Exception as e:
                print(f"Warning: Could not compare with last state {last_state_path}: {e}")
        if self.history_index < len(self.history) - 1:
            paths_to_delete = [state["path"] for state in self.history[self.history_index + 1 :]]
            self.history = self.history[: self.history_index + 1]
            for file_path in paths_to_delete:
                try:
                    os.remove(file_path)
                except OSError as e:
                    print(f"Warning: Could not delete orphaned state {file_path}: {e}")
        state_uuid = uuid.uuid4()
        new_state_filename = f"state-{state_uuid}.json"
        new_state_path = os.path.join(self.history_dir, new_state_filename)
        state_data = {
            "timestamp": timestamp_str,
            "selected_files": current_files,
            "selected_items": current_selected_items,
            "selection_mode": current_mode,
            "selected_file": current_sel_file,
            "file_content_hashes": content_hashes,
            "text_content": current_text,
        }
        try:
            with open(new_state_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)
        except OSError as e:
            QMessageBox.critical(self, "History Error", f"Could not save state:\n{new_state_path}\n{e}")
            return
        self.history.append({"path": new_state_path, "timestamp": timestamp_str})
        self.history_index = len(self.history) - 1
        self._update_history_ui(content_hashes)

    def _load_state_from_path(self, json_file_path: str) -> dict | None:
        try:
            with open(json_file_path, encoding="utf-8") as f:
                state_data = json.load(f)
            if (
                not isinstance(state_data.get("selected_files"), list)
                or not isinstance(state_data.get("text_content"), str)
                or not isinstance(state_data.get("file_content_hashes"), dict)
            ):
                raise ValueError("Invalid state file format or missing hashes")
            return state_data
        except FileNotFoundError:
            QMessageBox.critical(self, "History Error", f"State file not found:\n{json_file_path}")
        except (json.JSONDecodeError, ValueError) as e:
            QMessageBox.critical(self, "History Error", f"Invalid state file:\n{json_file_path}\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "History Error", f"Error loading state:\n{json_file_path}\n{e}")
        return None

    def _apply_loaded_state(self, state_data: dict):
        self._is_loading_state = True
        try:
            self.currentFiles = state_data.get("selected_files", [])
            self.selected_items = state_data.get("selected_items", [])
            self.selection_mode = state_data.get("selection_mode", "All Files")
            self.selected_file = state_data.get("selected_file", None)
            self._update_ui_for_new_files()
            text_content = state_data.get("text_content", "")
            self.textEdit.blockSignals(True)
            self.textEdit.setPlainText(text_content)
            self.textEdit.blockSignals(False)
            self.updateLineCountAndCopyButton()
        finally:
            self._is_loading_state = False

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            state_path = self.history[self.history_index]["path"]
            loaded_data = self._load_state_from_path(state_path)
            if loaded_data:
                self._apply_loaded_state(loaded_data)
                self._update_history_ui(loaded_data.get("file_content_hashes"))
            else:
                self._update_history_ui()

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            state_path = self.history[self.history_index]["path"]
            loaded_data = self._load_state_from_path(state_path)
            if loaded_data:
                self._apply_loaded_state(loaded_data)
                self._update_history_ui(loaded_data.get("file_content_hashes"))
            else:
                self._update_history_ui()

    def _update_history_ui(self, current_content_hashes: dict | None = None):
        history_len = len(self.history)
        can_go_back = self.history_index > 0
        can_go_forward = self.history_index < history_len - 1
        self.backAction.setEnabled(can_go_back)
        self.forwardAction.setEnabled(can_go_forward)
        self.historyStatusLabel.setText(
            f"History: {self.history_index + 1} of {history_len}" if history_len > 0 else "History: 0 of 0"
        )
        stale_status, status_text = "current", ""
        if self.history_index >= 0:
            if current_content_hashes is None:
                state_path = self.history[self.history_index]["path"]
                loaded_data = self._load_state_from_path(state_path)

                if loaded_data:
                    current_content_hashes = loaded_data.get("file_content_hashes")

            if current_content_hashes is not None:
                stale_status = self._check_file_freshness(current_content_hashes)
            if stale_status == "modified":
                status_text = "(Modified)"
            elif stale_status == "missing":
                status_text = "(Missing Files)"
            elif stale_status == "error":
                status_text = "(Check Error)"
        if status_text:
            self.staleIndicatorLabel.setText(status_text)
            self.staleIndicatorLabel.show()
        else:
            self.staleIndicatorLabel.setText("")
            self.staleIndicatorLabel.hide()

    def _check_file_freshness(self, stored_content_hashes: dict) -> str:
        if not stored_content_hashes:
            return "current"
        modified, missing, error_checking = False, False, False
        for f_path, stored_hash in stored_content_hashes.items():
            try:
                check_path = str(Path(f_path).resolve())
            except Exception:
                check_path = f_path
            current_hash = self._calculate_file_hash(check_path)
            if current_hash != stored_hash:
                if current_hash == HASH_MISSING_SENTINEL and stored_hash != HASH_MISSING_SENTINEL:
                    missing = True
                elif current_hash == HASH_ERROR_SENTINEL:
                    error_checking = True
                elif stored_hash in (HASH_MISSING_SENTINEL, HASH_ERROR_SENTINEL) and current_hash not in (
                    HASH_MISSING_SENTINEL,
                    HASH_ERROR_SENTINEL,
                ):
                    modified = True
                    break
                elif stored_hash not in (HASH_MISSING_SENTINEL, HASH_ERROR_SENTINEL):
                    modified = True
                    break
                else:
                    if current_hash == HASH_MISSING_SENTINEL:
                        missing = True
                    if current_hash == HASH_ERROR_SENTINEL:
                        error_checking = True
        if modified:
            return "modified"
        if missing:
            return "missing"
        if error_checking:
            return "error"
        return "current"

    def _poll_stale_status(self):
        if self.history_index < 0 or self._is_loading_state:
            return
        state_path = self.history[self.history_index]["path"]
        loaded_data = self._load_state_from_path(state_path)
        if loaded_data:
            content_hashes = loaded_data.get("file_content_hashes")
            if content_hashes is not None:
                stale_status = self._check_file_freshness(content_hashes)
                status_text = ""
                if stale_status == "modified":
                    status_text = "(Modified)"
                elif stale_status == "missing":
                    status_text = "(Missing Files)"
                elif stale_status == "error":
                    status_text = "(Check Error)"
                if status_text:
                    self.staleIndicatorLabel.setText(status_text)
                    self.staleIndicatorLabel.show()
                else:
                    self.staleIndicatorLabel.setText("")
                    self.staleIndicatorLabel.hide()

    # --- Cleanup ---
    def _cleanup_history_files(self, specific_dir: str | None = None):
        """Deletes history files. If specific_dir is None, uses self.history_dir."""
        target_dir = specific_dir if specific_dir is not None else self.history_dir

        if not target_dir or not os.path.isdir(target_dir):
            if specific_dir is None:
                print(f"History directory '{target_dir}' not found/set, skipping cleanup.")
            return
        print(f"Cleaning up history files in: {target_dir}")
        deleted_count, error_count = 0, 0
        try:
            for filename in os.listdir(target_dir):
                if filename.startswith("state-") and filename.endswith(".json"):
                    file_path = os.path.join(target_dir, filename)
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except OSError as e:
                        print(f"Error deleting file {file_path}: {e}")
                        error_count += 1
            if specific_dir is None and error_count == 0 and not os.listdir(target_dir):
                try:
                    os.rmdir(target_dir)
                    print(f"Removed empty history directory: {target_dir}")
                except OSError as e:
                    print(f"Could not remove history directory {target_dir}: {e}")
        except Exception as e:
            print(f"Error during history cleanup in {target_dir}: {e}")
        print(f"Cleanup in {target_dir}: {deleted_count} files deleted, {error_count} errors.")


# --- Utility Functions ---
def read_file_contents(file_path: str) -> str:
    encodings = ["utf-8", "latin-1", "cp1252"]
    last_error = None
    for enc in encodings:
        try:
            with open(file_path, encoding=enc) as file:
                return file.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except OSError as e:
            raise OSError(f"Could not read file {file_path}: {e}") from e
    raise UnicodeError(f"Could not decode {file_path}. Last error: {last_error}")


def parse_python_file(file_path: str) -> tuple[list[str], list[str], list[str], str]:
    try:
        file_content = read_file_contents(file_path)
        tree = ast.parse(file_content, filename=file_path)
    except SyntaxError as e:
        raise SyntaxError(f"Syntax error in {Path(file_path).name}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Error processing {Path(file_path).name}: {e}") from e
    classes, functions, imports = [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            try:
                segment = ast.get_source_segment(file_content, node)

                if segment:
                    imports.append(segment)
            except Exception:
                pass  # Ignore if segment fails
    return classes, functions, imports, file_content


def extract_code_and_imports(file_content: str, selected_items: list[str], sanitized_path: str) -> str:
    if not isinstance(selected_items, list):
        selected_items = []
    try:
        tree = ast.parse(file_content)
    except SyntaxError:
        return f"# Error parsing {sanitized_path}\n..."
    selected_code_blocks = []
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            try:
                segment = ast.get_source_segment(file_content, node)

                if segment:
                    imports.add(segment)
            except Exception:
                pass
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef | ast.FunctionDef) and node.name in selected_items:
            try:
                code_block = ast.get_source_segment(file_content, node)
                if code_block:
                    ref_name = node.name
                    block_type = "Class" if isinstance(node, ast.ClassDef) else "Function"
                    header = f"## {block_type}: {ref_name} (from {sanitized_path})"
                    selected_code_blocks.append(f"{header}\n\n```python\n{code_block}\n```\n")
            except Exception:
                selected_code_blocks.append(f"# Error extracting {node.name}...\n")
    if selected_code_blocks:
        imports_str = "\n".join(sorted(list(imports)))
        import_section = f"# Imports for {sanitized_path}\n```python\n{imports_str}\n```\n\n" if imports else ""
        actual_selected = [
            item for item in selected_items if any(f": {item}" in block for block in selected_code_blocks)
        ]
        sel_info = f"# Selected: {', '.join(actual_selected)}\n\n" if actual_selected else ""
        return f"# File: {sanitized_path}\n{sel_info}{import_section}" + "\n".join(selected_code_blocks)
    return ""


# --- Application Entry Point ---
if __name__ == "__main__":
    QApplication.setOrganizationName("Bastet")
    QApplication.setApplicationName("FileKitty")
    app = QApplication(sys.argv)
    ex = FilePicker()
    ex.show()
    sys.exit(app.exec_())
