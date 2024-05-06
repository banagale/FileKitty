import os

from PyQt5.QtGui import QIcon, QGuiApplication
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtWidgets import QListWidget

ICON_PATH = 'assets/icon/FileKitty-icon.png'


class FilePicker(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('FileKitty')
        self.setWindowIcon(QIcon(ICON_PATH))

        layout = QVBoxLayout(self)

        # Add a QListWidget to display the selected files
        self.fileList = QListWidget(self)
        layout.addWidget(self.fileList)

        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        layout.addWidget(self.textEdit)

        layout.setStretchFactor(self.fileList, 1)
        layout.setStretchFactor(self.textEdit, 2)

        btnOpen = QPushButton('📂  Select Files', self)
        btnOpen.clicked.connect(self.openFiles)
        layout.addWidget(btnOpen)

        self.btnCopy = QPushButton('📋  Copy to Clipboard', self)
        self.btnCopy.clicked.connect(self.copyToClipboard)
        self.btnCopy.setEnabled(False)
        layout.addWidget(self.btnCopy)

        # Calculate the appropriate heights using rounded pixel values
        base_height = self.btnCopy.sizeHint().height()
        increased_height = round(base_height * 2)  # Double the base height for the copy button
        slightly_increased_height = round(base_height * 1.1)  # Increase by 10% for the open button

        # Apply the calculated heights in the style sheets
        self.btnCopy.setStyleSheet(
            "QPushButton {min-height: %dpx; border-radius: 10px; border: 2px solid #555;}" % increased_height)
        btnOpen.setStyleSheet(
            "QPushButton {min-height: %dpx; border-radius: 6px; border: 2px solid #555;}" % slightly_increased_height)

        self.textEdit.textChanged.connect(self.updateCopyButtonState)

    def openFiles(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "Select files to concatenate", "",
                                                "All Files (*);;Text Files (*.txt)", options=options)

        if files:
            # Clear the list widget and add the selected files
            self.fileList.clear()
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
        self.btnCopy.setEnabled(bool(self.textEdit.toPlainText()))


if __name__ == '__main__':
    app = QApplication([])
    app.setWindowIcon(QIcon(ICON_PATH))
    ex = FilePicker()
    ex.show()
    app.exec_()
