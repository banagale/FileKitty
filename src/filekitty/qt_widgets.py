from PyQt5.QtCore import QMimeData, Qt, QStandardPaths, QUrl
from PyQt5.QtGui import QDrag, QMouseEvent
from PyQt5.QtWidgets import QPushButton, QTextEdit, QMessageBox, QWidget
from pathlib import Path
from datetime import datetime

# --- Drag Out Button ---
class DragOutButton(QPushButton):
    def __init__(self, text_edit: QTextEdit, parent: QWidget | None = None):
        super().__init__("📤 Drag Out as file", parent)
        self.setToolTip("Drag this button to export as a Markdown file")
        self.text_edit = text_edit
        self._temp_file_path: str | None = None
        self.setAcceptDrops(False)  # Button itself doesn't accept drops

    def mouseMoveEvent(self, event: QMouseEvent):
        # Start drag only on left button move
        if event.buttons() != Qt.LeftButton:
            super().mouseMoveEvent(event)  # Allow normal button behavior otherwise
            return

        content = self.text_edit.toPlainText()
        if not content.strip():
            return  # Don't drag if no content

        # --- Create a temporary file ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation))
        if not temp_dir.exists():
            # Handle case where temp location might not exist (unlikely but possible)
            print("Warning: Default temporary location not found, cannot create drag file.")
            return
        temp_file = temp_dir / f"FileKitty_{timestamp}.md"

        try:
            temp_file.write_text(content, encoding="utf-8")
            self._temp_file_path = str(temp_file)

            # --- Track file for cleanup (using parent FilePicker instance) ---
            if hasattr(self.parent(), "_dragged_out_temp_files"):
                self.parent()._dragged_out_temp_files.append(self._temp_file_path)

        except OSError as e:
            print(f"Error creating temporary file for drag: {e}")
            QMessageBox.warning(self.parent(), "Drag Error", f"Could not create temporary file:\n{e}")
            return  # Abort drag if file creation fails

        # --- Prepare MIME data ---
        mime_data = QMimeData()
        # Provide the file URL for file system drops
        mime_data.setUrls([QUrl.fromLocalFile(self._temp_file_path)])
        # Provide the text content for direct text drops (e.g., into text editors)
        mime_data.setText(content)

        # --- Execute the drag operation ---
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        # Suggest CopyAction, but target application decides final action
        # Note: drag.exec_() blocks until drop is complete
        drag.exec_(Qt.CopyAction)

        # --- Cleanup attempt (optional, immediate) ---
        # We register cleanup via atexit instead for robustness
        # if self._temp_file_path:
        #     try:
        #         # os.remove(self._temp_file_path)
        #         pass # Let atexit handle it
        #     except OSError as e:
        #         print(f"Note: Could not immediately remove temp drag file {self._temp_file_path}: {e}")
        #     self._temp_file_path = None
