import os

from PyQt5.QtCore import QSettings
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QGuiApplication, QKeySequence, QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import (QApplication, QWidget, QFileDialog, QVBoxLayout, QPushButton, QTextEdit,
                             QLabel, QListWidget, QDialog, QLineEdit, QHBoxLayout, QAction, QMenuBar)
from PyQt5.QtWidgets import QGraphicsColorizeEffect

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
        self.setWindowTitle('FileKitty')
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setGeometry(100, 100, 800, 600)
        self.setAcceptDrops(True)
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
            concatenated_content = self.concatenate_files(files)
            self.textEdit.setText(concatenated_content)

    def concatenate_files(self, files):
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
        return concatenated_content.rstrip()

    def copyToClipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.textEdit.toPlainText())

    def updateCopyButtonState(self):
        text = self.textEdit.toPlainText()
        line_count = text.count('\n') + 1 if text else 0
        self.lineCountLabel.setText(f'Lines ready to copy: {line_count}')
        self.btnCopy.setEnabled(bool(text))

    def refreshFiles(self):
        if hasattr(self, 'currentFiles') and self.currentFiles:
            concatenated_content = self.concatenate_files(self.currentFiles)
            self.textEdit.setText(concatenated_content)

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
                self.fileList.clear()
                self.currentFiles = files
                self.refreshFiles()
                self.btnRefresh.setEnabled(True)
                self.animateDropSuccess()
            event.acceptProposedAction()
        else:
            event.ignore()

    def applyBrightnessEffect(self):
        self.effect = QGraphicsColorizeEffect(self)
        self.effect.setColor(Qt.darkBlue)
        self.effect.setStrength(0.25)
        self.setGraphicsEffect(self.effect)

    def removeBrightnessEffect(self):
        self.setGraphicsEffect(None)

    def animateDropSuccess(self):
        self.applyBrightnessEffect()
        QTimer.singleShot(100, self.removeBrightnessEffect)


if __name__ == '__main__':
    app = QApplication([])
    app.setOrganizationName('YourCompany')
    app.setApplicationName('FileKitty')
    app.setWindowIcon(QIcon(ICON_PATH))
    ex = FilePicker()
    ex.show()
    app.exec_()
