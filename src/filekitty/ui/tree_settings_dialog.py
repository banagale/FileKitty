from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from filekitty.constants import (
    SETTINGS_TREE_BASE_KEY,
    SETTINGS_TREE_IGNORE_KEY,
    TREE_IGNORE_DEFAULT,
)


class TreeSettingsDialog(QDialog):
    """Modal opened by the gear next to “Include File Tree.”"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("File Tree Settings")
        self.setMinimumWidth(500)
        self._init_ui()
        self._load_settings()

    # ---------- UI ---------- #
    def _init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Base directory
        self.base_edit = QLineEdit(self)
        browse_btn = QPushButton("Browse…", self)
        browse_btn.clicked.connect(self._browse_dir)
        base_row = QHBoxLayout()
        base_row.addWidget(self.base_edit, 1)
        base_row.addWidget(browse_btn)
        form.addRow(QLabel("Lock Tree Base Directory:"), base_row)

        # Ignore regex
        self.ignore_edit = QLineEdit(self)
        form.addRow(QLabel("Ignore Regex:"), self.ignore_edit)

        layout.addLayout(form)

        note = QLabel("Defaults can be changed in Preferences → Tree tab.", self)
        note.setWordWrap(True)
        layout.addWidget(note)

        btn_row = QHBoxLayout()
        ok_btn = QPushButton("OK", self)
        cancel_btn = QPushButton("Cancel", self)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    # ---------- helpers ---------- #
    def _browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Base Directory")
        if path:
            self.base_edit.setText(path)

    def _load_settings(self):
        stg = QSettings("Bastet", "FileKitty")
        self.base_edit.setText(stg.value(SETTINGS_TREE_BASE_KEY, ""))
        self.ignore_edit.setText(stg.value(SETTINGS_TREE_IGNORE_KEY, TREE_IGNORE_DEFAULT))

    def accept(self):
        stg = QSettings("Bastet", "FileKitty")
        stg.setValue(SETTINGS_TREE_BASE_KEY, self.base_edit.text().strip())
        stg.setValue(SETTINGS_TREE_IGNORE_KEY, self.ignore_edit.text().strip())
        super().accept()
