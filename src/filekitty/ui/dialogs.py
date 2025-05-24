import os
from pathlib import Path

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from filekitty.constants import HISTORY_DIR_NAME, SETTINGS_DEFAULT_PATH_KEY, SETTINGS_HISTORY_PATH_KEY
from filekitty.core.python_parser import parse_python_file
from filekitty.core.utils import is_text_file


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

        # --- Include Date Modified Checkbox ---
        self.includeTimestampCheck = QCheckBox("Add Date Modified to Output by Default", self)
        settings = QSettings("Bastet", "FileKitty")
        include_timestamp = settings.value("includeDateModified", "true")
        self.includeTimestampCheck.setChecked(include_timestamp == "true")
        formLayout.addRow(self.includeTimestampCheck)

        # --- Use LLM Optimized Timestamp Format ---
        self.useLlmTimestampCheck = QCheckBox("Use LLM Optimized Timestamp Format (ISO 8601)", self)
        use_llm_timestamp = settings.value("useLlmTimestamp", "false")
        self.useLlmTimestampCheck.setChecked(use_llm_timestamp == "true")
        self.useLlmTimestampCheck.setEnabled(self.includeTimestampCheck.isChecked())
        formLayout.addRow(self.useLlmTimestampCheck)

        self.includeTimestampCheck.stateChanged.connect(self.updateLlmTimestampEnabled)

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

    def updateLlmTimestampEnabled(self, state):
        # Disable the LLM checkbox if the main "include timestamp" box is unchecked
        self.useLlmTimestampCheck.setEnabled(state == Qt.Checked)

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

        self.history_path_changed = history_path != self.initial_history_base_path

        settings = QSettings("Bastet", "FileKitty")
        settings.setValue(SETTINGS_DEFAULT_PATH_KEY, self.get_default_path())
        settings.setValue(SETTINGS_HISTORY_PATH_KEY, history_path)
        settings.setValue("includeDateModified", "true" if self.includeTimestampCheck.isChecked() else "false")
        settings.setValue("useLlmTimestamp", "true" if self.useLlmTimestampCheck.isChecked() else "false")
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
