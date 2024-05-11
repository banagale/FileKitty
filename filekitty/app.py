import os

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QIcon, QGuiApplication, QKeySequence
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QVBoxLayout, QPushButton, QTextEdit, QLabel, \
    QListWidget, QDialog, QLineEdit, QHBoxLayout, QAction

ICON_PATH = 'assets/icon/FileKitty-icon.png'


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super(PreferencesDialog, self).__init__(parent)
        self.setWindowTitle('Preferences')
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
        btnSave = QPushButton('Save')
        btnCancel = QPushButton('Cancel')
        btnLayout.addWidget(btnSave)
        btnLayout.addWidget(btnCancel)

        btnSave.clicked.connect(self.accept)
        btnCancel.clicked.connect(self.reject)

        layout.addLayout(btnLayout)
        self.setLayout(layout)

    def browsePath(self):
        # Opens a dialog to choose a directory
        dir_path = QFileDialog.getExistingDirectory(self, "Select Default Directory")
        if dir_path:
            self.pathEdit.setText(dir_path)

    def get_path(self):
        return self.pathEdit.text()

    def set_path(self, path):
        self.pathEdit.setText(path)


class FilePicker(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.createActions()

    def initUI(self):
        self.setWindowTitle('FileKitty')
        self.setWindowIcon(QIcon(ICON_PATH))

        layout = QVBoxLayout(self)

        self.fileList = QListWidget(self)
        layout.addWidget(self.fileList)

        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        layout.addWidget(self.textEdit)

        self.lineCountLabel = QLabel('Lines ready to copy: 0', self)
        layout.addWidget(self.lineCountLabel)

        self.btnRefresh = QPushButton('🔄 Refresh Text from Files', self)
        self.btnRefresh.clicked.connect(self.refreshFiles)
        self.btnRefresh.setEnabled(False)
        layout.addWidget(self.btnRefresh)

        btnOpen = QPushButton('📂 Select Files', self)
        btnOpen.clicked.connect(self.openFiles)
        layout.addWidget(btnOpen)

        self.btnCopy = QPushButton('📋 Copy to Clipboard', self)
        self.btnCopy.clicked.connect(self.copyToClipboard)
        self.btnCopy.setEnabled(False)
        layout.addWidget(self.btnCopy)

        self.textEdit.textChanged.connect(self.updateCopyButtonState)

    def createActions(self):
        self.prefAction = QAction("Preferences", self, shortcut=QKeySequence("Ctrl+,"))
        self.prefAction.triggered.connect(self.showPreferences)
        self.addAction(self.prefAction)

    def showPreferences(self):
        dialog = PreferencesDialog(self)
        dialog.set_path(self.get_default_path())
        if dialog.exec_():
            new_path = dialog.get_path()
            self.set_default_path(new_path)

    def get_default_path(self):
        settings = QSettings('YourCompany', 'FileKitty')
        return settings.value('defaultPath', '')

    def set_default_path(self, path):
        settings = QSettings('YourCompany', 'FileKitty')
        settings.setValue('defaultPath', path)

    def openFiles(self):
        default_path = self.get_default_path() or ""
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "Select files to concatenate", default_path,
                                                "All Files (*);;Text Files (*.txt)", options=options)
        if files:
            self.fileList.clear()
            self.currentFiles = files
            self.refreshFiles()
            self.btnRefresh.setEnabled(True)

            common_prefix = os.path.commonpath(files)
            common_prefix = os.path.dirname(common_prefix) if os.path.dirname(common_prefix) else common_prefix
            concatenated_content = ""
            for file in files:
                relative_path = os.path.relpath(file, start=common_prefix)
                self.fileList.addItem(relative_path)

                concatenated_content += f"### `{relative_path}`\n\n```\n"
                with open(file, 'r', encoding='utf-8') as file:
                    content = file.read()
                    concatenated_content += content
                concatenated_content += "\n```\n\n"
            self.textEdit.setText(concatenated_content)

    def copyToClipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.textEdit.toPlainText())

    def updateCopyButtonState(self):
        text = self.textEdit.toPlainText()
        line_count = text.count('\n') + 1 if text else 0
        self.lineCountLabel.setText(f'Lines ready to copy: {line_count}')
        self.btnCopy.setEnabled(bool(text))
        self.btnRefresh.setEnabled(bool(text))

    def refreshFiles(self):
        if hasattr(self, 'currentFiles') and self.currentFiles:
            common_prefix = os.path.commonpath(self.currentFiles)
            common_prefix = os.path.dirname(common_prefix) if os.path.dirname(common_prefix) else common_prefix
            concatenated_content = ""
            for file_path in self.currentFiles:
                relative_path = os.path.relpath(file_path, start=common_prefix)
                concatenated_content += f"### `{relative_path}`\n\n```\n"
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    concatenated_content += content
                concatenated_content += "\n```\n\n"
            concatenated_content = concatenated_content.rstrip()
            self.textEdit.setText(concatenated_content)


if __name__ == '__main__':
    app = QApplication([])
    app.setOrganizationName('YourCompany')
    app.setApplicationName('FileKitty')
    app.setWindowIcon(QIcon(ICON_PATH))
    ex = FilePicker()
    ex.show()
    app.exec_()
