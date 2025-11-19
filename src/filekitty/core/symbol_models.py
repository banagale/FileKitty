"""
Universal symbol data models for multi-language code extraction.

This module defines the data structures used to represent code symbols
(functions, classes, methods, etc.) across different programming languages.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SymbolType(Enum):
    """Types of code symbols that can be extracted."""

    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    TRAIT = "trait"
    ENUM = "enum"
    CONSTANT = "constant"
    VARIABLE = "variable"
    MODULE = "module"
    NAMESPACE = "namespace"
    IMPORT = "import"
    TYPE_ALIAS = "type_alias"
    PROTOCOL = "protocol"
    EXTENSION = "extension"
    MACRO = "macro"
    PROCEDURE = "procedure"
    TABLE = "table"
    VIEW = "view"
    COMPONENT = "component"  # React/Vue/etc components


@dataclass
class SymbolLocation:
    """Location information for a symbol in source code."""

    file_path: str
    start_line: int
    end_line: int
    start_column: int = 0
    end_column: int = 0

    @property
    def line_range(self) -> tuple[int, int]:
        """Return tuple of (start_line, end_line)."""
        return (self.start_line, self.end_line)

    def __str__(self) -> str:
        return f"{self.file_path}:{self.start_line}-{self.end_line}"


@dataclass
class Symbol:
    """
    Universal representation of a code symbol.

    This class represents symbols from any programming language with
    a unified interface for extraction, display, and analysis.
    """

    name: str
    symbol_type: SymbolType
    language: str
    location: SymbolLocation
    signature: str = ""
    docstring: str | None = None
    code: str = ""
    parent: str | None = None  # Parent class/module name
    modifiers: list[str] = field(default_factory=list)  # public, static, async, etc.
    dependencies: list[str] = field(default_factory=list)  # Imported symbols this depends on
    exports: bool = False  # Whether this symbol is exported/public
    metadata: dict[str, Any] = field(default_factory=dict)  # Language-specific extras

    @property
    def qualified_name(self) -> str:
        """Return fully qualified name including parent."""
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name

    @property
    def is_public(self) -> bool:
        """Check if symbol is publicly accessible."""
        if "public" in self.modifiers:
            return True
        if "private" in self.modifiers or "protected" in self.modifiers:
            return False
        return self.exports

    def __str__(self) -> str:
        return f"{self.symbol_type.value} {self.qualified_name} ({self.language})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "symbol_type": self.symbol_type.value,
            "language": self.language,
            "location": {
                "file_path": self.location.file_path,
                "start_line": self.location.start_line,
                "end_line": self.location.end_line,
                "start_column": self.location.start_column,
                "end_column": self.location.end_column,
            },
            "signature": self.signature,
            "docstring": self.docstring,
            "code": self.code,
            "parent": self.parent,
            "modifiers": self.modifiers,
            "dependencies": self.dependencies,
            "exports": self.exports,
            "metadata": self.metadata,
        }


@dataclass
class ExtractionResult:
    """Result of symbol extraction from a file."""

    file_path: str
    language: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True

    def get_symbols_by_type(self, symbol_type: SymbolType) -> list[Symbol]:
        """Get all symbols of a specific type."""
        return [s for s in self.symbols if s.symbol_type == symbol_type]

    def get_public_symbols(self) -> list[Symbol]:
        """Get all public symbols."""
        return [s for s in self.symbols if s.is_public]

    def get_symbol_by_name(self, name: str) -> Symbol | None:
        """Find a symbol by name."""
        for symbol in self.symbols:
            if symbol.name == name or symbol.qualified_name == name:
                return symbol
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file_path": self.file_path,
            "language": self.language,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": self.imports,
            "errors": self.errors,
            "success": self.success,
        }
