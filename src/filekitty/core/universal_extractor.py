"""
Universal symbol extractor using Tree-sitter for multi-language support.

This module provides symbol extraction capabilities for 15+ programming languages
using Tree-sitter parsers for accurate, syntax-aware code analysis.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

try:
    from tree_sitter import Language, Parser, Node
except ImportError:
    # Graceful fallback if tree-sitter not installed
    Language = None
    Parser = None
    Node = None

from filekitty.core.symbol_models import ExtractionResult, Symbol, SymbolLocation, SymbolType


class BaseExtractor(ABC):
    """Base class for language-specific symbol extractors."""

    def __init__(self, language_name: str):
        self.language_name = language_name
        self.parser = None
        self._init_parser()

    @abstractmethod
    def _init_parser(self) -> None:
        """Initialize the tree-sitter parser for this language."""
        pass

    @abstractmethod
    def extract_symbols(self, code: str, file_path: str) -> ExtractionResult:
        """
        Extract symbols from source code.

        Args:
            code: Source code as string
            file_path: Path to the source file

        Returns:
            ExtractionResult containing all extracted symbols
        """
        pass

    def _get_node_text(self, node: Any, code_bytes: bytes) -> str:
        """Extract text content from a tree-sitter node."""
        if Node is None or not isinstance(node, Node):
            return ""
        return code_bytes[node.start_byte : node.end_byte].decode("utf-8")

    def _get_location(self, node: Any, file_path: str) -> SymbolLocation:
        """Create SymbolLocation from tree-sitter node."""
        if Node is None or not isinstance(node, Node):
            return SymbolLocation(file_path, 0, 0, 0, 0)

        return SymbolLocation(
            file_path=file_path,
            start_line=node.start_point[0] + 1,  # Tree-sitter uses 0-based indexing
            end_line=node.end_point[0] + 1,
            start_column=node.start_point[1],
            end_column=node.end_point[1],
        )

    def _extract_docstring(self, node: Any, code_bytes: bytes) -> str | None:
        """Extract docstring/documentation comment for a node."""
        # Default implementation - override in language-specific extractors
        return None

    def _get_modifiers(self, node: Any) -> list[str]:
        """Extract modifiers (public, static, async, etc.) from a node."""
        # Default implementation - override in language-specific extractors
        return []


class JavaScriptExtractor(BaseExtractor):
    """Extractor for JavaScript and TypeScript code."""

    def __init__(self, is_typescript: bool = False):
        self.is_typescript = is_typescript
        lang_name = "typescript" if is_typescript else "javascript"
        super().__init__(lang_name)

    def _init_parser(self) -> None:
        """Initialize JavaScript/TypeScript parser."""
        if Parser is None:
            return

        try:
            if self.is_typescript:
                import tree_sitter_typescript as ts_typescript

                self.parser = Parser()
                self.parser.set_language(ts_typescript.language_typescript())
            else:
                import tree_sitter_javascript as ts_javascript

                self.parser = Parser()
                self.parser.set_language(ts_javascript.language())
        except Exception:
            # Fallback if tree-sitter languages not available
            self.parser = None

    def extract_symbols(self, code: str, file_path: str) -> ExtractionResult:
        """Extract symbols from JavaScript/TypeScript code."""
        result = ExtractionResult(file_path=file_path, language=self.language_name)

        if self.parser is None:
            result.errors.append("JavaScript/TypeScript parser not available")
            result.success = False
            return result

        try:
            code_bytes = code.encode("utf-8")
            tree = self.parser.parse(code_bytes)
            self._traverse_tree(tree.root_node, code_bytes, result)
        except Exception as e:
            result.errors.append(f"Parse error: {str(e)}")
            result.success = False

        return result

    def _traverse_tree(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Recursively traverse the syntax tree and extract symbols."""
        if Node is None:
            return

        node_type = node.type

        # Extract functions
        if node_type in ("function_declaration", "function"):
            self._extract_function(node, code_bytes, result)

        # Extract arrow functions assigned to variables
        elif node_type == "lexical_declaration" or node_type == "variable_declaration":
            self._extract_variable_function(node, code_bytes, result)

        # Extract classes
        elif node_type == "class_declaration":
            self._extract_class(node, code_bytes, result)

        # Extract methods
        elif node_type == "method_definition":
            self._extract_method(node, code_bytes, result)

        # Extract imports
        elif node_type in ("import_statement", "import_declaration"):
            self._extract_import(node, code_bytes, result)

        # TypeScript-specific: interfaces, types, enums
        elif self.is_typescript:
            if node_type == "interface_declaration":
                self._extract_interface(node, code_bytes, result)
            elif node_type == "type_alias_declaration":
                self._extract_type_alias(node, code_bytes, result)
            elif node_type == "enum_declaration":
                self._extract_enum(node, code_bytes, result)

        # Recursively process children
        for child in node.children:
            self._traverse_tree(child, code_bytes, result)

    def _extract_function(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract function declaration."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        # Extract function signature
        params_node = node.child_by_field_name("parameters")
        params = self._get_node_text(params_node, code_bytes) if params_node else "()"

        modifiers = []
        # Check if async
        if any(child.type == "async" for child in node.children):
            modifiers.append("async")
        # Check if export
        if node.parent and node.parent.type == "export_statement":
            modifiers.append("export")

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.FUNCTION,
            language=self.language_name,
            location=location,
            signature=f"function {name}{params}",
            code=code,
            modifiers=modifiers,
            exports="export" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_variable_function(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract arrow functions assigned to variables."""
        for child in node.children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                value_node = child.child_by_field_name("value")

                if name_node and value_node and value_node.type == "arrow_function":
                    name = self._get_node_text(name_node, code_bytes)
                    location = self._get_location(child, result.file_path)
                    code = self._get_node_text(child, code_bytes)

                    modifiers = []
                    if node.parent and node.parent.type == "export_statement":
                        modifiers.append("export")

                    symbol = Symbol(
                        name=name,
                        symbol_type=SymbolType.FUNCTION,
                        language=self.language_name,
                        location=location,
                        signature=f"const {name} = ()",
                        code=code,
                        modifiers=modifiers,
                        exports="export" in modifiers,
                    )

                    result.symbols.append(symbol)

    def _extract_class(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract class declaration."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        if node.parent and node.parent.type == "export_statement":
            modifiers.append("export")

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.CLASS,
            language=self.language_name,
            location=location,
            signature=f"class {name}",
            code=code,
            modifiers=modifiers,
            exports="export" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_method(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract method definition from a class."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        # Find parent class
        parent_name = None
        current = node.parent
        while current:
            if current.type == "class_declaration":
                class_name_node = current.child_by_field_name("name")
                if class_name_node:
                    parent_name = self._get_node_text(class_name_node, code_bytes)
                break
            current = current.parent

        modifiers = []
        for child in node.children:
            if child.type in ("static", "async", "public", "private", "protected"):
                modifiers.append(child.type)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.METHOD,
            language=self.language_name,
            location=location,
            signature=f"{name}()",
            code=code,
            parent=parent_name,
            modifiers=modifiers,
        )

        result.symbols.append(symbol)

    def _extract_import(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract import statement."""
        import_text = self._get_node_text(node, code_bytes)
        result.imports.append(import_text)

    def _extract_interface(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract TypeScript interface."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        if node.parent and node.parent.type == "export_statement":
            modifiers.append("export")

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.INTERFACE,
            language=self.language_name,
            location=location,
            signature=f"interface {name}",
            code=code,
            modifiers=modifiers,
            exports="export" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_type_alias(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract TypeScript type alias."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        if node.parent and node.parent.type == "export_statement":
            modifiers.append("export")

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.TYPE_ALIAS,
            language=self.language_name,
            location=location,
            signature=f"type {name}",
            code=code,
            modifiers=modifiers,
            exports="export" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_enum(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract TypeScript enum."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        if node.parent and node.parent.type == "export_statement":
            modifiers.append("export")

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.ENUM,
            language=self.language_name,
            location=location,
            signature=f"enum {name}",
            code=code,
            modifiers=modifiers,
            exports="export" in modifiers,
        )

        result.symbols.append(symbol)

class GoExtractor(BaseExtractor):
    """Extractor for Go code."""

    def __init__(self):
        super().__init__("go")

    def _init_parser(self) -> None:
        """Initialize Go parser."""
        if Parser is None:
            return

        try:
            import tree_sitter_go as ts_go

            self.parser = Parser()
            self.parser.set_language(ts_go.language())
        except Exception:
            self.parser = None

    def extract_symbols(self, code: str, file_path: str) -> ExtractionResult:
        """Extract symbols from Go code."""
        result = ExtractionResult(file_path=file_path, language=self.language_name)

        if self.parser is None:
            result.errors.append("Go parser not available")
            result.success = False
            return result

        try:
            code_bytes = code.encode("utf-8")
            tree = self.parser.parse(code_bytes)
            self._traverse_tree(tree.root_node, code_bytes, result)
        except Exception as e:
            result.errors.append(f"Parse error: {str(e)}")
            result.success = False

        return result

    def _traverse_tree(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Recursively traverse the syntax tree and extract symbols."""
        if Node is None:
            return

        node_type = node.type

        if node_type == "function_declaration":
            self._extract_function(node, code_bytes, result)
        elif node_type == "method_declaration":
            self._extract_method(node, code_bytes, result)
        elif node_type == "type_declaration":
            self._extract_type(node, code_bytes, result)
        elif node_type == "interface_type":
            self._extract_interface(node, code_bytes, result)
        elif node_type == "import_declaration":
            self._extract_import(node, code_bytes, result)

        for child in node.children:
            self._traverse_tree(child, code_bytes, result)

    def _extract_function(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Go function."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        # Check if function is exported (starts with uppercase)
        is_exported = name[0].isupper() if name else False

        params_node = node.child_by_field_name("parameters")
        params = self._get_node_text(params_node, code_bytes) if params_node else "()"

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.FUNCTION,
            language=self.language_name,
            location=location,
            signature=f"func {name}{params}",
            code=code,
            exports=is_exported,
        )

        result.symbols.append(symbol)

    def _extract_method(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Go method."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        # Get receiver type
        receiver_node = node.child_by_field_name("receiver")
        receiver = None
        if receiver_node:
            receiver_text = self._get_node_text(receiver_node, code_bytes)
            # Extract type name from receiver (e.g., "(s *Server)" -> "Server")
            import re

            match = re.search(r"\*?(\w+)", receiver_text)
            if match:
                receiver = match.group(1)

        is_exported = name[0].isupper() if name else False

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.METHOD,
            language=self.language_name,
            location=location,
            signature=f"func {name}()",
            code=code,
            parent=receiver,
            exports=is_exported,
        )

        result.symbols.append(symbol)

    def _extract_type(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Go type declaration."""
        for child in node.children:
            if child.type == "type_spec":
                name_node = child.child_by_field_name("name")
                type_node = child.child_by_field_name("type")

                if name_node and type_node:
                    name = self._get_node_text(name_node, code_bytes)
                    location = self._get_location(child, result.file_path)
                    code = self._get_node_text(child, code_bytes)

                    is_exported = name[0].isupper() if name else False

                    # Determine if it's a struct or other type
                    symbol_type = SymbolType.STRUCT if type_node.type == "struct_type" else SymbolType.TYPE_ALIAS

                    symbol = Symbol(
                        name=name,
                        symbol_type=symbol_type,
                        language=self.language_name,
                        location=location,
                        signature=f"type {name}",
                        code=code,
                        exports=is_exported,
                    )

                    result.symbols.append(symbol)

    def _extract_interface(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Go interface."""
        # Interface extraction is handled in _extract_type
        pass

    def _extract_import(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Go import."""
        import_text = self._get_node_text(node, code_bytes)
        result.imports.append(import_text)
