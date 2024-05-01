from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QVBoxLayout, QPushButton, QTextEdit
import os


class FilePicker(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('File Picker and Concatenator')
        layout = QVBoxLayout(self)

        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        layout.addWidget(self.textEdit)

        btnOpen = QPushButton('Open Files', self)
        btnOpen.clicked.connect(self.openFiles)
        layout.addWidget(btnOpen)

    def openFiles(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "Select files to concatenate", "",
                                                "All Files (*);;Text Files (*.txt)", options=options)
        if files:
            common_prefix = os.path.commonpath(files)
            # Move one directory up unless it's already the root directory
            common_prefix = os.path.dirname(common_prefix) if os.path.dirname(common_prefix) else common_prefix
            concatenated_content = ""
            for file in files:
                relative_path = os.path.relpath(file, start=common_prefix)
                concatenated_content += f"### `{relative_path}`\n\n```text\n"
                with open(file, 'r', encoding='utf-8') as file:
                    content = file.read()
                    concatenated_content += content
                concatenated_content += "\n```\n\n"
            self.textEdit.setText(concatenated_content)


if __name__ == '__main__':
    app = QApplication([])
    ex = FilePicker()
    ex.show()
    app.exec_()
