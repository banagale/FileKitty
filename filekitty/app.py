from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QVBoxLayout, QPushButton, QTextEdit


class FilePicker(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('File Picker and Concatenator')
        layout = QVBoxLayout(self)

        self.textEdit = QTextEdit(self)
        layout.addWidget(self.textEdit)

        btnOpen = QPushButton('Open File', self)
        btnOpen.clicked.connect(self.openFile)
        layout.addWidget(btnOpen)

    def openFile(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(self, "Select files to concatenate", "",
                                                "All Files (*);;Text Files (*.txt)", options=options)
        if files:
            concatenated_content = ""
            for file in files:
                with open(file, 'r') as file:
                    content = file.read()
                    concatenated_content += content + "\n"
            self.textEdit.setText(concatenated_content)


if __name__ == '__main__':
    app = QApplication([])
    ex = FilePicker()
    ex.show()
    app.exec_()
