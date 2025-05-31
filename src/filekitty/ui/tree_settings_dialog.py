from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from filekitty.constants import (
    SETTINGS_TREE_BASE_KEY,
    SETTINGS_TREE_DEF_IGNORE_KEY,
    SETTINGS_TREE_IGNORE_KEY,
    TREE_IGNORE_DEFAULT,
)


class TreeSettingsDialog(QDialog):
    """Per-window tree settings. Blank fields mean ‘use global default’."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("File Tree Settings")
        self.setMinimumWidth(500)
        self._build_ui()
        self._load()

    # ---------- UI ---------- #
    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        # base dir
        self.base_edit = QLineEdit()
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.base_edit, 1)
        row.addWidget(browse)
        form.addRow("Lock Tree Base Directory:", row)

        # ignore list
        self.ignore_edit = QTextEdit()
        self.ignore_edit.setMinimumHeight(60)
        form.addRow("Ignore List / Regex:", self.ignore_edit)

        # divergence label
        self.divergeLabel = QLabel("foo")  # Initialize with space so it has height
        self.divergeLabel.setWordWrap(True)  # Allow wrapping for long messages
        self.divergeLabel.setMinimumHeight(24)  # Prevent collapse to 0
        self.divergeLabel.setText("Tree ignore list differs from Preferences.")
        layout.addWidget(self.divergeLabel)

        note = QLabel("Leave fields blank to inherit defaults from Preferences.", self)
        note.setWordWrap(True)
        layout.addWidget(note)

        # buttons
        btnRow = QHBoxLayout()
        ok, cancel = QPushButton("OK"), QPushButton("Cancel")
        btnRow.addStretch()
        btnRow.addWidget(ok)
        btnRow.addWidget(cancel)
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        layout.addLayout(btnRow)

    # ---------- helpers ---------- #
    def _browse(self):
        p = QFileDialog.getExistingDirectory(self, "Select Tree Base Directory")
        if p:
            self.base_edit.setText(p)

    def _load(self):
        s = QSettings("Bastet", "FileKitty")
        self.base_edit.setText(s.value(SETTINGS_TREE_BASE_KEY, ""))
        self.ignore_edit.setPlainText(s.value(SETTINGS_TREE_IGNORE_KEY, ""))

        # show divergence notice
        default_ignore = s.value(SETTINGS_TREE_DEF_IGNORE_KEY, TREE_IGNORE_DEFAULT).strip()
        current_ignore = self.ignore_edit.toPlainText().strip() or default_ignore
        if current_ignore != default_ignore:
            self.divergeLabel.setText("Ignores differ from global default.")
        else:
            self.divergeLabel.setText("")

    def accept(self):
        s = QSettings("Bastet", "FileKitty")
        s.setValue(SETTINGS_TREE_BASE_KEY, self.base_edit.text().strip())
        s.setValue(SETTINGS_TREE_IGNORE_KEY, self.ignore_edit.toPlainText().strip())
        super().accept()
