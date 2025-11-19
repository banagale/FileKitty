"""
Universal Symbol Selection Dialog for multi-language code extraction.

This dialog allows users to select symbols (classes, functions, methods, etc.)
from files in any supported programming language.
"""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from filekitty.core.extractor_factory import ExtractorFactory
from filekitty.core.symbol_models import SymbolType
from filekitty.core.utils import is_text_file


class UniversalSymbolDialog(QDialog):
    """
    Dialog for selecting code symbols from multiple programming languages.

    Supports JavaScript/TypeScript, Go, Rust, Java, C/C++, Ruby, PHP, C#, Bash, and more.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Code Symbols")
        self.parent = parent
        self.selected_items = []
        self.resize(700, 500)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Mode and File Selection Layout
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Selection Mode:"))
        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems(["All Files", "Single File"])
        self.mode_combo.currentTextChanged.connect(self.update_file_selection)
        mode_layout.addWidget(self.mode_combo)

        self.file_combo = QComboBox(self)
        self.file_combo.setVisible(False)
        self.file_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.file_combo.currentTextChanged.connect(self.update_symbols)
        mode_layout.addWidget(self.file_combo)
        layout.addLayout(mode_layout)

        # Info label showing supported languages
        info_label = QLabel("Supports: JavaScript/TypeScript, Go, Rust, Java, C/C++, Ruby, PHP, C#, Bash, Python")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)

        # List Widget for Symbols
        self.symbolList = QListWidget(self)
        layout.addWidget(self.symbolList)

        # Buttons
        button_layout = QHBoxLayout()
        self.btnSelectAll = QPushButton("Select All", self)
        self.btnSelectAll.clicked.connect(self.select_all)
        button_layout.addWidget(self.btnSelectAll)

        self.btnDeselectAll = QPushButton("Deselect All", self)
        self.btnDeselectAll.clicked.connect(self.deselect_all)
        button_layout.addWidget(self.btnDeselectAll)

        button_layout.addStretch()

        self.btnOk = QPushButton("OK", self)
        self.btnOk.clicked.connect(self.accept)
        button_layout.addWidget(self.btnOk)

        self.btnCancel = QPushButton("Cancel", self)
        self.btnCancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btnCancel)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        # Initialize based on parent state
        if self.parent:
            initial_mode = getattr(self.parent, "selection_mode", "All Files")
            self.mode_combo.setCurrentText(initial_mode)
            self.update_file_selection(initial_mode)
            if initial_mode == "Single File" and hasattr(self.parent, "selected_file") and self.parent.selected_file:
                file_name = Path(self.parent.selected_file).name
                if self.file_combo.findText(file_name) != -1:
                    self.file_combo.setCurrentText(file_name)
        else:
            self.update_file_selection("All Files")

    def update_file_selection(self, mode):
        """Update file selection combo based on mode."""
        self.file_combo.setVisible(mode == "Single File")
        self.file_combo.clear()

        if mode == "Single File":
            if not self.parent:
                self.symbolList.clear()
                self.symbolList.addItem("No parent window available")
                return

            # List all supported files
            supported_files = []
            for f in getattr(self.parent, "currentFiles", []):
                if is_text_file(f) and ExtractorFactory.supports_file(f):
                    supported_files.append(f)

            if not supported_files:
                self.symbolList.clear()
                self.symbolList.addItem("No supported files available")
            else:
                for f in supported_files:
                    name = Path(f).name
                    self.file_combo.addItem(name)

                # Set to previously selected file if available
                if hasattr(self.parent, "selected_file") and self.parent.selected_file:
                    current_selection_name = Path(self.parent.selected_file).name
                    if self.file_combo.findText(current_selection_name) != -1:
                        self.file_combo.setCurrentText(current_selection_name)
                    else:
                        self.file_combo.setCurrentIndex(0)
                else:
                    self.file_combo.setCurrentIndex(0)

                self.update_symbols(self.file_combo.currentText())
        else:
            self.populate_all_files()

    def update_symbols(self, file_name):
        """Update symbol list for a single file."""
        self.symbolList.clear()

        if not file_name or not self.parent:
            return

        # Find the full path
        selected_file = next(
            (f for f in getattr(self.parent, "currentFiles", []) if Path(f).name == file_name), None
        )

        if not selected_file:
            self.symbolList.addItem(f"File '{file_name}' not found")
            return

        if not is_text_file(selected_file):
            self.symbolList.addItem(f"File '{file_name}' is not a text file")
            return

        # Extract symbols using universal extractor
        try:
            with open(selected_file, "r", encoding="utf-8") as f:
                code = f.read()

            result = ExtractorFactory.extract_symbols(code, selected_file)

            if not result or not result.success:
                error_msg = result.errors[0] if result and result.errors else "Unknown error"
                self.symbolList.addItem(f"Error parsing file: {error_msg}")
                return

            if not result.symbols:
                self.symbolList.addItem("No symbols found in file")
                return

            # Group symbols by type
            symbol_groups = {}
            for symbol in result.symbols:
                symbol_type = symbol.symbol_type
                if symbol_type not in symbol_groups:
                    symbol_groups[symbol_type] = []
                symbol_groups[symbol_type].append(symbol)

            # Display symbols grouped by type
            for symbol_type in sorted(symbol_groups.keys(), key=lambda x: x.value):
                # Add header
                header = QListWidgetItem(f"{symbol_type.value.capitalize()}s:")
                header.setFlags(Qt.ItemIsEnabled)
                header.setForeground(QColor(Qt.darkBlue))
                header.setFont(header.font())
                self.symbolList.addItem(header)

                # Add symbols
                for symbol in symbol_groups[symbol_type]:
                    display_name = symbol.qualified_name if symbol.parent else symbol.name
                    item_text = f"  {display_name}"

                    # Add signature hint
                    if symbol.signature:
                        item_text += f" - {symbol.signature}"

                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, symbol.name)  # Store actual symbol name
                    item.setCheckState(Qt.Unchecked)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    self.symbolList.addItem(item)

        except Exception as e:
            self.symbolList.addItem(f"Error: {str(e)}")

    def populate_all_files(self):
        """Populate symbol list for all files."""
        self.symbolList.clear()

        if not self.parent:
            self.symbolList.addItem("No parent window available")
            return

        has_content = False
        file_symbols = {}

        # Extract symbols from all supported files
        for file_path in getattr(self.parent, "currentFiles", []):
            if not is_text_file(file_path) or not ExtractorFactory.supports_file(file_path):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()

                result = ExtractorFactory.extract_symbols(code, file_path)

                if result and result.success and result.symbols:
                    file_symbols[file_path] = result.symbols
                    has_content = True
            except Exception:
                # Silently skip files that can't be parsed
                pass

        if not has_content:
            self.symbolList.addItem("No symbols found in supported files")
            return

        # Display symbols grouped by file
        for file_path, symbols in file_symbols.items():
            # File header
            file_header = QListWidgetItem(f"📄 {Path(file_path).name}")
            file_header.setFlags(Qt.ItemIsEnabled)
            file_header.setForeground(QColor(Qt.darkGreen))
            font = file_header.font()
            font.setBold(True)
            file_header.setFont(font)
            self.symbolList.addItem(file_header)

            # Group symbols by type
            symbol_groups = {}
            for symbol in symbols:
                symbol_type = symbol.symbol_type
                if symbol_type not in symbol_groups:
                    symbol_groups[symbol_type] = []
                symbol_groups[symbol_type].append(symbol)

            # Display symbols grouped by type
            for symbol_type in sorted(symbol_groups.keys(), key=lambda x: x.value):
                # Type header
                type_header = QListWidgetItem(f"  {symbol_type.value.capitalize()}s:")
                type_header.setFlags(Qt.ItemIsEnabled)
                type_header.setForeground(QColor(Qt.darkGray))
                self.symbolList.addItem(type_header)

                # Symbols
                for symbol in symbol_groups[symbol_type]:
                    display_name = symbol.qualified_name if symbol.parent else symbol.name
                    item_text = f"    {display_name}"

                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, symbol.name)  # Store actual symbol name
                    item.setCheckState(Qt.Unchecked)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    self.symbolList.addItem(item)

    def select_all(self):
        """Select all checkable items."""
        for i in range(self.symbolList.count()):
            item = self.symbolList.item(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(Qt.Checked)

    def deselect_all(self):
        """Deselect all checkable items."""
        for i in range(self.symbolList.count()):
            item = self.symbolList.item(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(Qt.Unchecked)

    def accept(self):
        """Gather selected items before closing."""
        self.selected_items = []
        for i in range(self.symbolList.count()):
            item = self.symbolList.item(i)
            if item.flags() & Qt.ItemIsUserCheckable and item.checkState() == Qt.Checked:
                # Get the actual symbol name stored in UserRole
                symbol_name = item.data(Qt.UserRole)
                if symbol_name:
                    self.selected_items.append(symbol_name)
        super().accept()

    def get_selected_items(self):
        """Return list of selected symbol names."""
        return self.selected_items

    def get_mode(self):
        """Return current selection mode."""
        return self.mode_combo.currentText()

    def get_selected_file(self):
        """Return selected file path in Single File mode."""
        if self.mode_combo.currentText() == "Single File" and self.parent:
            file_name = self.file_combo.currentText()
            return next((f for f in getattr(self.parent, "currentFiles", []) if Path(f).name == file_name), None)
        return None
