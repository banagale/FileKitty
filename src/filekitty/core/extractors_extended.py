"""
Extended language extractors for Rust, Java, C/C++, Ruby, PHP, C#, Bash, Swift and more.

This module provides additional tree-sitter based extractors for various programming languages.
"""

from typing import Any

try:
    from tree_sitter import Parser, Node
except ImportError:
    Parser = None
    Node = None

from filekitty.core.symbol_models import ExtractionResult, Symbol, SymbolType
from filekitty.core.universal_extractor import BaseExtractor


class RustExtractor(BaseExtractor):
    """Extractor for Rust code."""

    def __init__(self):
        super().__init__("rust")

    def _init_parser(self) -> None:
        """Initialize Rust parser."""
        if Parser is None:
            return

        try:
            import tree_sitter_rust as ts_rust

            self.parser = Parser()
            self.parser.set_language(ts_rust.language())
        except Exception:
            self.parser = None

    def extract_symbols(self, code: str, file_path: str) -> ExtractionResult:
        """Extract symbols from Rust code."""
        result = ExtractionResult(file_path=file_path, language=self.language_name)

        if self.parser is None:
            result.errors.append("Rust parser not available")
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

        if node_type == "function_item":
            self._extract_function(node, code_bytes, result)
        elif node_type == "impl_item":
            self._extract_impl(node, code_bytes, result)
        elif node_type == "struct_item":
            self._extract_struct(node, code_bytes, result)
        elif node_type == "enum_item":
            self._extract_enum(node, code_bytes, result)
        elif node_type == "trait_item":
            self._extract_trait(node, code_bytes, result)
        elif node_type == "mod_item":
            self._extract_module(node, code_bytes, result)
        elif node_type == "use_declaration":
            self._extract_use(node, code_bytes, result)

        for child in node.children:
            self._traverse_tree(child, code_bytes, result)

    def _extract_function(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Rust function."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type == "visibility_modifier":
                modifiers.append("pub")
            elif child.type == "async":
                modifiers.append("async")
            elif child.type == "const":
                modifiers.append("const")

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.FUNCTION,
            language=self.language_name,
            location=location,
            signature=f"fn {name}()",
            code=code,
            modifiers=modifiers,
            exports="pub" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_impl(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Rust impl block (methods)."""
        type_node = node.child_by_field_name("type")
        type_name = self._get_node_text(type_node, code_bytes) if type_node else None

        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "function_item":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        name = self._get_node_text(name_node, code_bytes)
                        location = self._get_location(child, result.file_path)
                        code = self._get_node_text(child, code_bytes)

                        modifiers = []
                        for subchild in child.children:
                            if subchild.type == "visibility_modifier":
                                modifiers.append("pub")

                        symbol = Symbol(
                            name=name,
                            symbol_type=SymbolType.METHOD,
                            language=self.language_name,
                            location=location,
                            signature=f"fn {name}()",
                            code=code,
                            parent=type_name,
                            modifiers=modifiers,
                            exports="pub" in modifiers,
                        )

                        result.symbols.append(symbol)

    def _extract_struct(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Rust struct."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type == "visibility_modifier":
                modifiers.append("pub")

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.STRUCT,
            language=self.language_name,
            location=location,
            signature=f"struct {name}",
            code=code,
            modifiers=modifiers,
            exports="pub" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_enum(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Rust enum."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type == "visibility_modifier":
                modifiers.append("pub")

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.ENUM,
            language=self.language_name,
            location=location,
            signature=f"enum {name}",
            code=code,
            modifiers=modifiers,
            exports="pub" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_trait(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Rust trait."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type == "visibility_modifier":
                modifiers.append("pub")

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.TRAIT,
            language=self.language_name,
            location=location,
            signature=f"trait {name}",
            code=code,
            modifiers=modifiers,
            exports="pub" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_module(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Rust module."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)

        modifiers = []
        for child in node.children:
            if child.type == "visibility_modifier":
                modifiers.append("pub")

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.MODULE,
            language=self.language_name,
            location=location,
            signature=f"mod {name}",
            code="",
            modifiers=modifiers,
            exports="pub" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_use(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Rust use statement."""
        use_text = self._get_node_text(node, code_bytes)
        result.imports.append(use_text)


class JavaExtractor(BaseExtractor):
    """Extractor for Java code."""

    def __init__(self):
        super().__init__("java")

    def _init_parser(self) -> None:
        """Initialize Java parser."""
        if Parser is None:
            return

        try:
            import tree_sitter_java as ts_java

            self.parser = Parser()
            self.parser.set_language(ts_java.language())
        except Exception:
            self.parser = None

    def extract_symbols(self, code: str, file_path: str) -> ExtractionResult:
        """Extract symbols from Java code."""
        result = ExtractionResult(file_path=file_path, language=self.language_name)

        if self.parser is None:
            result.errors.append("Java parser not available")
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

        if node_type == "class_declaration":
            self._extract_class(node, code_bytes, result)
        elif node_type == "interface_declaration":
            self._extract_interface(node, code_bytes, result)
        elif node_type == "method_declaration":
            self._extract_method(node, code_bytes, result)
        elif node_type == "enum_declaration":
            self._extract_enum(node, code_bytes, result)
        elif node_type == "import_declaration":
            self._extract_import(node, code_bytes, result)

        for child in node.children:
            self._traverse_tree(child, code_bytes, result)

    def _extract_class(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Java class."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                mod_text = self._get_node_text(child, code_bytes)
                modifiers.extend(mod_text.split())

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.CLASS,
            language=self.language_name,
            location=location,
            signature=f"class {name}",
            code=code,
            modifiers=modifiers,
            exports="public" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_interface(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Java interface."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                mod_text = self._get_node_text(child, code_bytes)
                modifiers.extend(mod_text.split())

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.INTERFACE,
            language=self.language_name,
            location=location,
            signature=f"interface {name}",
            code=code,
            modifiers=modifiers,
            exports="public" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_method(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Java method."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        parent_name = None
        current = node.parent
        while current:
            if current.type in ("class_declaration", "interface_declaration"):
                class_name_node = current.child_by_field_name("name")
                if class_name_node:
                    parent_name = self._get_node_text(class_name_node, code_bytes)
                break
            current = current.parent

        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                mod_text = self._get_node_text(child, code_bytes)
                modifiers.extend(mod_text.split())

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.METHOD,
            language=self.language_name,
            location=location,
            signature=f"{name}()",
            code=code,
            parent=parent_name,
            modifiers=modifiers,
            exports="public" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_enum(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Java enum."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type == "modifiers":
                mod_text = self._get_node_text(child, code_bytes)
                modifiers.extend(mod_text.split())

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.ENUM,
            language=self.language_name,
            location=location,
            signature=f"enum {name}",
            code=code,
            modifiers=modifiers,
            exports="public" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_import(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Java import."""
        import_text = self._get_node_text(node, code_bytes)
        result.imports.append(import_text)


class CExtractor(BaseExtractor):
    """Extractor for C code."""

    def __init__(self):
        super().__init__("c")

    def _init_parser(self) -> None:
        """Initialize C parser."""
        if Parser is None:
            return

        try:
            import tree_sitter_c as ts_c

            self.parser = Parser()
            self.parser.set_language(ts_c.language())
        except Exception:
            self.parser = None

    def extract_symbols(self, code: str, file_path: str) -> ExtractionResult:
        """Extract symbols from C code."""
        result = ExtractionResult(file_path=file_path, language=self.language_name)

        if self.parser is None:
            result.errors.append("C parser not available")
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

        if node_type == "function_definition":
            self._extract_function(node, code_bytes, result)
        elif node_type == "struct_specifier":
            self._extract_struct(node, code_bytes, result)
        elif node_type == "enum_specifier":
            self._extract_enum(node, code_bytes, result)
        elif node_type == "preproc_include":
            self._extract_include(node, code_bytes, result)

        for child in node.children:
            self._traverse_tree(child, code_bytes, result)

    def _extract_function(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C function."""
        declarator = node.child_by_field_name("declarator")
        if declarator:
            # Navigate to function declarator
            while declarator and declarator.type != "function_declarator":
                if declarator.type == "pointer_declarator":
                    declarator = declarator.children[1] if len(declarator.children) > 1 else None
                else:
                    break

            if declarator and declarator.type == "function_declarator":
                name_node = declarator.child_by_field_name("declarator")
                if name_node:
                    name = self._get_node_text(name_node, code_bytes)
                    location = self._get_location(node, result.file_path)
                    code = self._get_node_text(node, code_bytes)

                    modifiers = []
                    # Check for static
                    for child in node.children:
                        if child.type == "storage_class_specifier":
                            mod_text = self._get_node_text(child, code_bytes)
                            modifiers.append(mod_text)

                    symbol = Symbol(
                        name=name,
                        symbol_type=SymbolType.FUNCTION,
                        language=self.language_name,
                        location=location,
                        signature=f"{name}()",
                        code=code,
                        modifiers=modifiers,
                        exports="static" not in modifiers,
                    )

                    result.symbols.append(symbol)

    def _extract_struct(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C struct."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.STRUCT,
            language=self.language_name,
            location=location,
            signature=f"struct {name}",
            code=code,
            exports=True,
        )

        result.symbols.append(symbol)

    def _extract_enum(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C enum."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.ENUM,
            language=self.language_name,
            location=location,
            signature=f"enum {name}",
            code=code,
            exports=True,
        )

        result.symbols.append(symbol)

    def _extract_include(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C #include."""
        include_text = self._get_node_text(node, code_bytes)
        result.imports.append(include_text)


class CppExtractor(CExtractor):
    """Extractor for C++ code (extends C extractor)."""

    def __init__(self):
        BaseExtractor.__init__(self, "cpp")

    def _init_parser(self) -> None:
        """Initialize C++ parser."""
        if Parser is None:
            return

        try:
            import tree_sitter_cpp as ts_cpp

            self.parser = Parser()
            self.parser.set_language(ts_cpp.language())
        except Exception:
            self.parser = None

    def _traverse_tree(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Recursively traverse the syntax tree and extract symbols."""
        if Node is None:
            return

        node_type = node.type

        if node_type == "function_definition":
            self._extract_function(node, code_bytes, result)
        elif node_type == "class_specifier":
            self._extract_class(node, code_bytes, result)
        elif node_type == "struct_specifier":
            self._extract_struct(node, code_bytes, result)
        elif node_type == "enum_specifier":
            self._extract_enum(node, code_bytes, result)
        elif node_type == "namespace_definition":
            self._extract_namespace(node, code_bytes, result)
        elif node_type == "preproc_include":
            self._extract_include(node, code_bytes, result)

        for child in node.children:
            self._traverse_tree(child, code_bytes, result)

    def _extract_class(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C++ class."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.CLASS,
            language=self.language_name,
            location=location,
            signature=f"class {name}",
            code=code,
            exports=True,
        )

        result.symbols.append(symbol)

    def _extract_namespace(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C++ namespace."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.NAMESPACE,
            language=self.language_name,
            location=location,
            signature=f"namespace {name}",
            code="",
            exports=True,
        )

        result.symbols.append(symbol)


class RubyExtractor(BaseExtractor):
    """Extractor for Ruby code."""

    def __init__(self):
        super().__init__("ruby")

    def _init_parser(self) -> None:
        """Initialize Ruby parser."""
        if Parser is None:
            return

        try:
            import tree_sitter_ruby as ts_ruby

            self.parser = Parser()
            self.parser.set_language(ts_ruby.language())
        except Exception:
            self.parser = None

    def extract_symbols(self, code: str, file_path: str) -> ExtractionResult:
        """Extract symbols from Ruby code."""
        result = ExtractionResult(file_path=file_path, language=self.language_name)

        if self.parser is None:
            result.errors.append("Ruby parser not available")
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

        if node_type == "method":
            self._extract_method(node, code_bytes, result)
        elif node_type == "class":
            self._extract_class(node, code_bytes, result)
        elif node_type == "module":
            self._extract_module(node, code_bytes, result)

        for child in node.children:
            self._traverse_tree(child, code_bytes, result)

    def _extract_method(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Ruby method."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        # Determine if it's a class method or instance method
        parent_name = None
        current = node.parent
        while current:
            if current.type == "class":
                class_name_node = current.child_by_field_name("name")
                if class_name_node:
                    parent_name = self._get_node_text(class_name_node, code_bytes)
                break
            current = current.parent

        symbol_type = SymbolType.METHOD if parent_name else SymbolType.FUNCTION

        symbol = Symbol(
            name=name,
            symbol_type=symbol_type,
            language=self.language_name,
            location=location,
            signature=f"def {name}",
            code=code,
            parent=parent_name,
            exports=True,
        )

        result.symbols.append(symbol)

    def _extract_class(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Ruby class."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.CLASS,
            language=self.language_name,
            location=location,
            signature=f"class {name}",
            code=code,
            exports=True,
        )

        result.symbols.append(symbol)

    def _extract_module(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Ruby module."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.MODULE,
            language=self.language_name,
            location=location,
            signature=f"module {name}",
            code=code,
            exports=True,
        )

        result.symbols.append(symbol)


class PHPExtractor(BaseExtractor):
    """Extractor for PHP code."""

    def __init__(self):
        super().__init__("php")

    def _init_parser(self) -> None:
        """Initialize PHP parser."""
        if Parser is None:
            return

        try:
            import tree_sitter_php as ts_php

            self.parser = Parser()
            self.parser.set_language(ts_php.language_php())
        except Exception:
            self.parser = None

    def extract_symbols(self, code: str, file_path: str) -> ExtractionResult:
        """Extract symbols from PHP code."""
        result = ExtractionResult(file_path=file_path, language=self.language_name)

        if self.parser is None:
            result.errors.append("PHP parser not available")
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

        if node_type == "function_definition":
            self._extract_function(node, code_bytes, result)
        elif node_type == "class_declaration":
            self._extract_class(node, code_bytes, result)
        elif node_type == "method_declaration":
            self._extract_method(node, code_bytes, result)
        elif node_type == "interface_declaration":
            self._extract_interface(node, code_bytes, result)
        elif node_type == "trait_declaration":
            self._extract_trait(node, code_bytes, result)
        elif node_type == "namespace_definition":
            self._extract_namespace(node, code_bytes, result)

        for child in node.children:
            self._traverse_tree(child, code_bytes, result)

    def _extract_function(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract PHP function."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.FUNCTION,
            language=self.language_name,
            location=location,
            signature=f"function {name}()",
            code=code,
            exports=True,
        )

        result.symbols.append(symbol)

    def _extract_class(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract PHP class."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type in ("abstract", "final"):
                modifiers.append(child.type)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.CLASS,
            language=self.language_name,
            location=location,
            signature=f"class {name}",
            code=code,
            modifiers=modifiers,
            exports=True,
        )

        result.symbols.append(symbol)

    def _extract_method(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract PHP method."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

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
            if child.type == "visibility_modifier":
                mod_text = self._get_node_text(child, code_bytes)
                modifiers.append(mod_text)
            elif child.type in ("static", "abstract", "final"):
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
            exports="public" in modifiers or not modifiers,
        )

        result.symbols.append(symbol)

    def _extract_interface(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract PHP interface."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.INTERFACE,
            language=self.language_name,
            location=location,
            signature=f"interface {name}",
            code=code,
            exports=True,
        )

        result.symbols.append(symbol)

    def _extract_trait(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract PHP trait."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.TRAIT,
            language=self.language_name,
            location=location,
            signature=f"trait {name}",
            code=code,
            exports=True,
        )

        result.symbols.append(symbol)

    def _extract_namespace(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract PHP namespace."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.NAMESPACE,
            language=self.language_name,
            location=location,
            signature=f"namespace {name}",
            code="",
            exports=True,
        )

        result.symbols.append(symbol)


class CSharpExtractor(BaseExtractor):
    """Extractor for C# code."""

    def __init__(self):
        super().__init__("csharp")

    def _init_parser(self) -> None:
        """Initialize C# parser."""
        if Parser is None:
            return

        try:
            import tree_sitter_c_sharp as ts_csharp

            self.parser = Parser()
            self.parser.set_language(ts_csharp.language())
        except Exception:
            self.parser = None

    def extract_symbols(self, code: str, file_path: str) -> ExtractionResult:
        """Extract symbols from C# code."""
        result = ExtractionResult(file_path=file_path, language=self.language_name)

        if self.parser is None:
            result.errors.append("C# parser not available")
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

        if node_type == "class_declaration":
            self._extract_class(node, code_bytes, result)
        elif node_type == "interface_declaration":
            self._extract_interface(node, code_bytes, result)
        elif node_type == "method_declaration":
            self._extract_method(node, code_bytes, result)
        elif node_type == "struct_declaration":
            self._extract_struct(node, code_bytes, result)
        elif node_type == "enum_declaration":
            self._extract_enum(node, code_bytes, result)
        elif node_type == "namespace_declaration":
            self._extract_namespace(node, code_bytes, result)
        elif node_type == "using_directive":
            self._extract_using(node, code_bytes, result)

        for child in node.children:
            self._traverse_tree(child, code_bytes, result)

    def _extract_class(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C# class."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type in ("public", "private", "protected", "internal", "static", "abstract", "sealed"):
                modifiers.append(child.type)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.CLASS,
            language=self.language_name,
            location=location,
            signature=f"class {name}",
            code=code,
            modifiers=modifiers,
            exports="public" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_interface(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C# interface."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type in ("public", "private", "protected", "internal"):
                modifiers.append(child.type)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.INTERFACE,
            language=self.language_name,
            location=location,
            signature=f"interface {name}",
            code=code,
            modifiers=modifiers,
            exports="public" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_method(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C# method."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        parent_name = None
        current = node.parent
        while current:
            if current.type in ("class_declaration", "struct_declaration", "interface_declaration"):
                class_name_node = current.child_by_field_name("name")
                if class_name_node:
                    parent_name = self._get_node_text(class_name_node, code_bytes)
                break
            current = current.parent

        modifiers = []
        for child in node.children:
            if child.type in ("public", "private", "protected", "internal", "static", "virtual", "override", "async"):
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
            exports="public" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_struct(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C# struct."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type in ("public", "private", "protected", "internal"):
                modifiers.append(child.type)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.STRUCT,
            language=self.language_name,
            location=location,
            signature=f"struct {name}",
            code=code,
            modifiers=modifiers,
            exports="public" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_enum(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C# enum."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        modifiers = []
        for child in node.children:
            if child.type in ("public", "private", "protected", "internal"):
                modifiers.append(child.type)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.ENUM,
            language=self.language_name,
            location=location,
            signature=f"enum {name}",
            code=code,
            modifiers=modifiers,
            exports="public" in modifiers,
        )

        result.symbols.append(symbol)

    def _extract_namespace(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C# namespace."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.NAMESPACE,
            language=self.language_name,
            location=location,
            signature=f"namespace {name}",
            code="",
            exports=True,
        )

        result.symbols.append(symbol)

    def _extract_using(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract C# using directive."""
        using_text = self._get_node_text(node, code_bytes)
        result.imports.append(using_text)


class BashExtractor(BaseExtractor):
    """Extractor for Bash/Shell scripts."""

    def __init__(self):
        super().__init__("bash")

    def _init_parser(self) -> None:
        """Initialize Bash parser."""
        if Parser is None:
            return

        try:
            import tree_sitter_bash as ts_bash

            self.parser = Parser()
            self.parser.set_language(ts_bash.language())
        except Exception:
            self.parser = None

    def extract_symbols(self, code: str, file_path: str) -> ExtractionResult:
        """Extract symbols from Bash code."""
        result = ExtractionResult(file_path=file_path, language=self.language_name)

        if self.parser is None:
            result.errors.append("Bash parser not available")
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

        if node_type == "function_definition":
            self._extract_function(node, code_bytes, result)

        for child in node.children:
            self._traverse_tree(child, code_bytes, result)

    def _extract_function(self, node: Any, code_bytes: bytes, result: ExtractionResult) -> None:
        """Extract Bash function."""
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return

        name = self._get_node_text(name_node, code_bytes)
        location = self._get_location(node, result.file_path)
        code = self._get_node_text(node, code_bytes)

        symbol = Symbol(
            name=name,
            symbol_type=SymbolType.FUNCTION,
            language=self.language_name,
            location=location,
            signature=f"{name}()",
            code=code,
            exports=True,
        )

        result.symbols.append(symbol)
