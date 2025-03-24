import ast
from pathlib import Path

from PyQt5.QtCore import QSettings, QStandardPaths, Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QGuiApplication, QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

ICON_PATH = "assets/icon/FileKitty-icon.png"


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.pathEdit = QLineEdit(self)
        self.pathEdit.setPlaceholderText("Enter or select default file path...")
        layout.addWidget(self.pathEdit)

        btnBrowse = QPushButton("Browse...")
        btnBrowse.clicked.connect(self.browsePath)
        layout.addWidget(btnBrowse)

        btnLayout = QHBoxLayout()
        btnSave = QPushButton("Save")
        btnCancel = QPushButton("Cancel")
        btnLayout.addWidget(btnSave)
        btnLayout.addWidget(btnCancel)

        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

        layout.addLayout(btnLayout)
        self.setLayout(layout)

    def browsePath(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Default Directory")
        if dir_path:
            self.pathEdit.setText(dir_path)

    def get_path(self):
        return self.pathEdit.text()

    def set_path(self, path):
        self.pathEdit.setText(path)

    def accept(self):
        settings = QSettings("Bastet", "FileKitty")
        settings.setValue("defaultPath", self.get_path())
        super().accept()


class SelectClassesFunctionsDialog(QDialog):
    def __init__(self, all_classes, all_functions, selected_items=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Classes/Functions")
        self.all_classes = all_classes
        self.all_functions = all_functions
        self.selected_items = selected_items if selected_items is not None else []
        self.parent = parent  # To access currentFiles
        self.resize(600, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Mode selection
        mode_layout = QHBoxLayout()
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(["All Files", "Single File"])
        self.mode_combo.currentTextChanged.connect(self.update_file_selection)
        mode_layout.addWidget(QLabel("Selection Mode:"))
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)

        # File selection for Single File mode
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
        self.update_file_selection("All Files")  # Initial population

    def update_file_selection(self, mode):
        self.file_combo.setVisible(mode == "Single File")
        self.file_combo.clear()
        if mode == "Single File":
            python_files = [f for f in self.parent.currentFiles if f.endswith(".py")]
            if not python_files:
                self.fileList.clear()
                self.fileList.addItem("No Python files available")
            else:
                self.file_combo.addItems([Path(f).name for f in python_files])
                self.update_symbols(Path(python_files[0]).name)
        else:
            self.populate_all_files()

    def update_symbols(self, file_name):
        self.fileList.clear()
        selected_file = next((f for f in self.parent.currentFiles if Path(f).name == file_name), None)
        if selected_file:
            classes, functions, _, _ = parse_python_file(selected_file)
            if not (classes or functions):
                self.fileList.addItem("No classes or functions found in this file")
            else:
                for cls in classes:
                    item = QListWidgetItem(f"Class: {cls}")
                    item.setCheckState(Qt.Checked if cls in self.selected_items else Qt.Unchecked)
                    self.fileList.addItem(item)
                for func in functions:
                    item = QListWidgetItem(f"Function: {func}")
                    item.setCheckState(Qt.Checked if func in self.selected_items else Qt.Unchecked)
                    self.fileList.addItem(item)
        else:
            self.fileList.addItem("File not found")

    def populate_all_files(self):
        self.fileList.clear()
        for file_path, classes in self.all_classes.items():
            file_header = QListWidgetItem(f"File: {Path(file_path).name} (Classes)")
            file_header.setFlags(file_header.flags() & ~Qt.ItemIsSelectable)
            self.fileList.addItem(file_header)
            for cls in classes:
                item = QListWidgetItem(f"Class: {cls}")
                item.setCheckState(Qt.Checked if cls in self.selected_items else Qt.Unchecked)
                self.fileList.addItem(item)

        for file_path, functions in self.all_functions.items():
            file_header = QListWidgetItem(f"File: {Path(file_path).name} (Functions)")
            file_header.setFlags(file_header.flags() & ~Qt.ItemIsSelectable)
            self.fileList.addItem(file_header)
            for func in functions:
                item = QListWidgetItem(f"Function: {func}")
                item.setCheckState(Qt.Checked if func in self.selected_items else Qt.Unchecked)
                self.fileList.addItem(item)

    def accept(self):
        self.selected_items = [
            item.text().split(": ")[1]
            for item in self.fileList.findItems("*", Qt.MatchWildcard)
            if item.checkState() == Qt.Checked
        ]
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


class FilePicker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FileKitty")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setGeometry(100, 100, 800, 600)
        self.setAcceptDrops(True)
        self.selected_items = []
        self.currentFiles = []
        self.selection_mode = "All Files"  # New state
        self.selected_file = None  # New state
        self.initUI()
        self.createActions()
        self.createMenu()
        self.default_path = self.get_default_path()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.fileList = QListWidget(self)
        layout.addWidget(self.fileList)

        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        layout.addWidget(self.textEdit)

        self.lineCountLabel = QLabel("Lines ready to copy: 0", self)
        layout.addWidget(self.lineCountLabel)

        btnOpen = QPushButton("📂 Select Files", self)
        btnOpen.clicked.connect(self.openFiles)
        layout.addWidget(btnOpen)

        self.btnSelectClassesFunctions = QPushButton("🔍 Select Classes/Functions", self)
        self.btnSelectClassesFunctions.clicked.connect(self.selectClassesFunctions)
        self.btnSelectClassesFunctions.setEnabled(False)
        layout.addWidget(self.btnSelectClassesFunctions)

        self.btnCopy = QPushButton("📋 Copy to Clipboard", self)
        self.btnCopy.clicked.connect(self.copyToClipboard)
        self.btnCopy.setEnabled(False)
        layout.addWidget(self.btnCopy)

        self.btnRefresh = QPushButton("🔄 Refresh", self)
        self.btnRefresh.clicked.connect(self.refreshText)
        self.btnRefresh.setEnabled(False)
        layout.addWidget(self.btnRefresh)

        self.textEdit.textChanged.connect(self.updateCopyButtonState)

        self.setLayout(layout)

    def createActions(self):
        self.prefAction = QAction("Preferences", self)
        self.prefAction.setShortcut(QKeySequence("Ctrl+,"))
        self.prefAction.triggered.connect(self.showPreferences)

    def createMenu(self):
        menubar = QMenuBar(self)
        appMenu = menubar.addMenu("FileKitty")
        appMenu.addAction(self.prefAction)
        self.layout().setMenuBar(menubar)

    def showPreferences(self):
        dialog = PreferencesDialog(self)
        dialog.set_path(self.get_default_path())
        if dialog.exec_():
            new_path = dialog.get_path()
            self.set_default_path(new_path)

    def get_default_path(self):
        settings = QSettings("Bastet", "FileKitty")
        return settings.value("defaultPath", QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation))

    def set_default_path(self, path):
        settings = QSettings("Bastet", "FileKitty")
        settings.setValue("defaultPath", path)

    def openFiles(self):
        default_path = self.get_default_path() or ""
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files to analyze",
            default_path,
            "All Files (*);;Python Files (*.py);;JavaScript Files (*.js);;TypeScript Files (*.ts *.tsx)",
            options=options,
        )
        if files:
            self.currentFiles = files
            self.fileList.clear()
            for file in files:
                sanitized_path = self.sanitize_path(file)
                self.fileList.addItem(sanitized_path)

            if all(file.endswith(".py") for file in files):
                self.btnSelectClassesFunctions.setEnabled(True)
            else:
                self.btnSelectClassesFunctions.setEnabled(False)
            self.btnRefresh.setEnabled(True)

            self.updateTextEdit()

    def selectClassesFunctions(self):
        """Allow selection of classes/functions from all or one selected Python file."""
        all_classes = {}
        all_functions = {}
        for file_path in self.currentFiles:
            if file_path.endswith(".py"):
                classes, functions, _, _ = parse_python_file(file_path)
                all_classes[file_path] = classes
                all_functions[file_path] = functions

        if all_classes or all_functions:
            dialog = SelectClassesFunctionsDialog(all_classes, all_functions, self.selected_items, self)
            if dialog.exec_():
                self.selected_items = dialog.get_selected_items()
                self.selection_mode = dialog.get_mode()
                self.selected_file = dialog.get_selected_file()
                self.updateTextEdit()

    def copyToClipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.textEdit.toPlainText())

    def updateCopyButtonState(self):
        text = self.textEdit.toPlainText()
        line_count = text.count("\n") + 1 if text else 0
        self.lineCountLabel.setText(f"Lines ready to copy: {line_count}")
        self.btnCopy.setEnabled(bool(text))
        self.btnRefresh.setEnabled(bool(text))

    def refreshText(self):
        """Refresh the text output with the latest file contents."""
        try:
            self.updateTextEdit()
        except Exception as e:
            QMessageBox.warning(self, "Refresh Error", f"Failed to refresh some files: {str(e)}")

    def sanitize_path(self, file_path):
        """Remove sensitive directory information from file paths."""
        path = Path(file_path)
        parts = path.parts
        if "Users" in parts:
            user_index = parts.index("Users")
            sanitized_parts = parts[:user_index] + parts[user_index + 2 :]
            return str(Path(*sanitized_parts))
        return str(path)

    def updateTextEdit(self):
        """Update the main text area with the content of selected files."""
        combined_code = ""
        files_to_process = (
            [self.selected_file] if self.selection_mode == "Single File" and self.selected_file else self.currentFiles
        )
        for file_path in files_to_process:
            sanitized_path = self.sanitize_path(file_path)
            if file_path.endswith(".py"):
                classes, functions, imports, file_content = parse_python_file(file_path)
                if not self.selected_items:
                    combined_code += f"# {sanitized_path}\n\n```python\n{file_content}\n```\n"
                else:
                    filtered_code = extract_code_and_imports(file_content, self.selected_items, sanitized_path)
                    if filtered_code.strip():
                        combined_code += filtered_code
            else:
                file_content = read_file_contents(file_path)
                combined_code += f"# {sanitized_path}\n\n```{self.detect_language(file_path)}\n{file_content}\n```\n"

        self.textEdit.setText(combined_code)

    def detect_language(self, file_path):
        """Detect the language based on the file extension for syntax highlighting in markdown."""
        if file_path.endswith(".js"):
            return "javascript"
        elif file_path.endswith((".ts", ".tsx")):
            return "typescript"
        else:
            return "plaintext"

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
                    files.append(url.toLocalFile())
            if files:
                self.currentFiles = files
                self.fileList.clear()
                for file in files:
                    sanitized_path = self.sanitize_path(file)
                    self.fileList.addItem(sanitized_path)

                if all(file.endswith(".py") for file in files):
                    self.btnSelectClassesFunctions.setEnabled(True)
                else:
                    self.btnSelectClassesFunctions.setEnabled(False)
                self.btnRefresh.setEnabled(True)

                self.updateTextEdit()
            event.acceptProposedAction()
        else:
            event.ignore()


def read_file_contents(file_path: str) -> str:
    with open(file_path, encoding="utf-8") as file:
        return file.read()


def parse_python_file(file_path: str) -> tuple[list[str], list[str], list[str], str]:
    try:
        file_content = read_file_contents(file_path)
        tree = ast.parse(file_content, filename=file_path)
    except SyntaxError as e:
        print(f"Syntax error in file {file_path}: {e}")
        return [], [], [], ""

    classes = []
    functions = []
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            imports.append(ast.get_source_segment(file_content, node))

    return classes, functions, imports, file_content


def extract_code_and_imports(file_content: str, selected_items: list[str], sanitized_path: str) -> str:
    tree = ast.parse(file_content)
    selected_code = []
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            imports.add(ast.get_source_segment(file_content, node))

    imports_str = "\n".join(sorted(imports))
    header = f"# {sanitized_path}\n\n## Selected Classes/Functions: {', '.join(selected_items)}\n"

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef | ast.FunctionDef) and node.name in selected_items:
            start_line = node.lineno - 1
            end_line = node.end_lineno
            code_block = "\n".join(file_content.splitlines()[start_line:end_line])
            reference_path = f"{sanitized_path.replace('/', '.')}.{node.name}"
            selected_code.append(f"### `{reference_path}`\n\n```python\n{code_block}\n```\n")

    if selected_code:
        return f"{header}\n```python\n{imports_str}\n```\n\n" + "\n".join(selected_code)
    # If no classes/functions are selected in this file, return an empty string
    return ""


if __name__ == "__main__":
    app = QApplication([])
    app.setOrganizationName("Bastet")
    app.setApplicationName("FileKitty")
    app.setWindowIcon(QIcon(ICON_PATH))
    ex = FilePicker()
    ex.show()
    app.exec_()
