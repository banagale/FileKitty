import ast
import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QGuiApplication, QKeySequence
from PyQt5.QtWidgets import (
    QApplication, QWidget, QFileDialog, QVBoxLayout, QPushButton, QTextEdit,
    QLabel, QListWidget, QDialog, QAction, QMenuBar
)
from PyQt5.QtWidgets import (
    QListWidgetItem
)

ICON_PATH = 'assets/icon/FileKitty-icon.png'


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super(PreferencesDialog, self).__init__(parent)
        self.setWindowTitle('Preferences')
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        self.setLayout(layout)


class SelectClassesFunctionsDialog(QDialog):
    def __init__(self, classes, functions, selected_items=None, parent=None):
        super(SelectClassesFunctionsDialog, self).__init__(parent)
        self.setWindowTitle('Select Classes/Functions')
        self.classes = classes
        self.functions = functions
        self.selected_items = selected_items if selected_items is not None else []
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.fileList = QListWidget(self)
        for cls in self.classes:
            item = QListWidgetItem(f"Class: {cls}")
            item.setCheckState(Qt.Checked if cls in self.selected_items else Qt.Unchecked)
            self.fileList.addItem(item)

        for func in self.functions:
            item = QListWidgetItem(f"Function: {func}")
            item.setCheckState(Qt.Checked if func in self.selected_items else Qt.Unchecked)
            self.fileList.addItem(item)

        layout.addWidget(self.fileList)

        self.btnOk = QPushButton('OK', self)
        self.btnOk.clicked.connect(self.accept)
        layout.addWidget(self.btnOk)

        self.setLayout(layout)

    def accept(self):
        self.selected_items = [
            item.text().split(": ")[1] for item in self.fileList.findItems("*", Qt.MatchWildcard)
            if item.checkState() == Qt.Checked
        ]
        super().accept()

    def get_selected_items(self):
        return self.selected_items


class FilePicker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('FileKitty')
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setGeometry(100, 100, 800, 600)
        self.selected_items = []  # Track selected items
        self.currentFiles = []  # Track current files
        self.initUI()
        self.createActions()
        self.createMenu()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.fileList = QListWidget(self)
        layout.addWidget(self.fileList)

        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        layout.addWidget(self.textEdit)

        self.lineCountLabel = QLabel('Lines ready to copy: 0', self)
        layout.addWidget(self.lineCountLabel)

        btnOpen = QPushButton('📂 Select Files', self)
        btnOpen.clicked.connect(self.openFiles)
        layout.addWidget(btnOpen)

        self.btnSelectClassesFunctions = QPushButton('🔍 Select Classes/Functions', self)
        self.btnSelectClassesFunctions.clicked.connect(self.selectClassesFunctions)
        self.btnSelectClassesFunctions.setEnabled(False)
        layout.addWidget(self.btnSelectClassesFunctions)

        self.btnCopy = QPushButton('📋 Copy to Clipboard', self)
        self.btnCopy.clicked.connect(self.copyToClipboard)
        self.btnCopy.setEnabled(False)
        layout.addWidget(self.btnCopy)

        self.textEdit.textChanged.connect(self.updateCopyButtonState)

        self.setLayout(layout)

    def createActions(self):
        self.prefAction = QAction("Preferences", self)
        self.prefAction.setShortcut(QKeySequence("Ctrl+,"))
        self.prefAction.triggered.connect(self.showPreferences)

    def createMenu(self):
        menubar = QMenuBar(self)
        appMenu = menubar.addMenu('FileKitty')
        appMenu.addAction(self.prefAction)
        self.layout().setMenuBar(menubar)

    def showPreferences(self):
        dialog = PreferencesDialog(self)
        dialog.exec_()

    def openFiles(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select files to analyze", "",
            "All Files (*);;Python Files (*.py);;JavaScript Files (*.js);;TypeScript Files (*.ts *.tsx)",
            options=options
        )
        if files:
            self.currentFiles = files
            self.fileList.clear()
            for file in files:
                self.fileList.addItem(file)

            # Check if all selected files are Python files to enable the class/function selection
            if all(file.endswith(('.py',)) for file in files):
                self.btnSelectClassesFunctions.setEnabled(True)
            else:
                self.btnSelectClassesFunctions.setEnabled(False)

            self.updateTextEdit()

    def selectClassesFunctions(self):
        if self.currentFiles:
            file_path = self.currentFiles[0]
            classes, functions, _, file_content = parse_python_file(file_path)
            dialog = SelectClassesFunctionsDialog(classes, functions, self.selected_items, self)
            if dialog.exec_():
                self.selected_items = dialog.get_selected_items()
                self.updateTextEdit()

    def copyToClipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.textEdit.toPlainText())

    def updateCopyButtonState(self):
        text = self.textEdit.toPlainText()
        line_count = text.count('\n') + 1 if text else 0
        self.lineCountLabel.setText(f'Lines ready to copy: {line_count}')
        self.btnCopy.setEnabled(bool(text))

    def updateTextEdit(self):
        if self.currentFiles:
            file_path = self.currentFiles[0]
            if file_path.endswith('.py'):
                _, _, imports, file_content = parse_python_file(file_path)
                if not self.selected_items:
                    code = f"# {os.path.basename(file_path)}\n\n```python\n{file_content}\n```"
                else:
                    code = extract_code_and_imports(file_content, self.selected_items, file_path)
            else:
                # For non-Python files, simply show the entire file content
                with open(file_path, 'r', encoding='utf-8') as file:
                    file_content = file.read()
                    code = f"# {os.path.basename(file_path)}\n\n```{self.detect_language(file_path)}\n{file_content}\n```"

            self.textEdit.setText(code)

    def detect_language(self, file_path):
        """Detect the language based on the file extension for syntax highlighting in markdown."""
        if file_path.endswith('.js'):
            return 'javascript'
        elif file_path.endswith(('.ts', '.tsx')):
            return 'typescript'
        else:
            return 'plaintext'


def parse_python_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
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
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(ast.get_source_segment(file_content, node))

    return classes, functions, imports, file_content


def extract_code_and_imports(file_content, selected_items, file_path):
    tree = ast.parse(file_content)
    selected_code = []
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.add(ast.get_source_segment(file_content, node))

    imports_str = "\n".join(sorted(imports))
    file_name = os.path.basename(file_path)
    header = f"# {file_name}\n\n## Selected Classes/Functions: {', '.join(selected_items)}\n"

    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in selected_items:
            start_line = node.lineno - 1
            end_line = node.end_lineno
            code_block = "\n".join(file_content.splitlines()[start_line:end_line])
            reference_path = f"{file_path.replace('/', '.')}.{node.name}"
            selected_code.append(f"### `{reference_path}`\n\n```python\n{code_block}\n```\n")

    return f"{header}\n```python\n{imports_str}\n```\n\n" + "\n".join(selected_code)


if __name__ == '__main__':
    app = QApplication([])
    app.setOrganizationName('YourCompany')
    app.setApplicationName('FileKitty')
    app.setWindowIcon(QIcon(ICON_PATH))
    ex = FilePicker()
    ex.show()
    app.exec_()
