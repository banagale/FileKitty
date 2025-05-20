import sys
from pathlib import Path

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtWidgets import QApplication

from .main_window import FilePicker


class FileKittyApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.main_window = None # Will be set in main()

    def event(self, e):
        if e.type() == QEvent.FileOpen: # QEvent.FileOpen needs to be imported
            file_path = e.file()
            print(f"Received file open event: {file_path}")
            if self.main_window:
                self.main_window.handle_external_file(file_path)
            return True
        return super().event(e)


def main():
    # Enable High DPI scaling for better visuals on modern displays
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = FileKittyApp(sys.argv)
    # Set Organization and Application Name for QSettings
    # This is typically done on the app instance itself
    app.setOrganizationName("Bastet")
    app.setApplicationName("FileKitty")

    # Apply a style if desired (optional)
    # app.setStyle("Fusion")

    # 🛠️ Filter out argv that are NOT files (basic safety)
    file_args = [arg for arg in sys.argv[1:] if Path(arg).is_file()]

    picker = FilePicker(initial_files=file_args)
    app.main_window = picker # Set the main_window attribute
    picker.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
