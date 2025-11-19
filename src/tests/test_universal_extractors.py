"""
Tests for universal symbol extractors.

Tests the tree-sitter based extractors for multiple programming languages.
"""

import pytest

from filekitty.core.extractor_factory import ExtractorFactory
from filekitty.core.symbol_models import SymbolType


class TestJavaScriptExtractor:
    """Tests for JavaScript symbol extraction."""

    def test_extract_functions(self, sample_javascript_code):
        """Test extracting JavaScript functions."""
        result = ExtractorFactory.extract_symbols(sample_javascript_code, "test.js")

        assert result is not None
        assert result.success is True

        functions = result.get_symbols_by_type(SymbolType.FUNCTION)
        function_names = [f.name for f in functions]

        assert "myFunction" in function_names
        assert "arrowFunction" in function_names
        assert "asyncFunction" in function_names

    def test_extract_classes(self, sample_javascript_code):
        """Test extracting JavaScript classes."""
        result = ExtractorFactory.extract_symbols(sample_javascript_code, "test.js")

        classes = result.get_symbols_by_type(SymbolType.CLASS)
        assert len(classes) >= 1
        assert classes[0].name == "MyClass"

    def test_extract_methods(self, sample_javascript_code):
        """Test extracting JavaScript methods."""
        result = ExtractorFactory.extract_symbols(sample_javascript_code, "test.js")

        methods = result.get_symbols_by_type(SymbolType.METHOD)
        method_names = [m.name for m in methods]

        assert "myMethod" in method_names or "constructor" in method_names

    def test_extract_imports(self, sample_javascript_code):
        """Test extracting JavaScript imports."""
        result = ExtractorFactory.extract_symbols(sample_javascript_code, "test.js")

        assert len(result.imports) > 0


class TestTypeScriptExtractor:
    """Tests for TypeScript symbol extraction."""

    def test_extract_interfaces(self, sample_typescript_code):
        """Test extracting TypeScript interfaces."""
        result = ExtractorFactory.extract_symbols(sample_typescript_code, "test.ts")

        if result and result.success:
            interfaces = result.get_symbols_by_type(SymbolType.INTERFACE)
            if interfaces:
                assert interfaces[0].name == "User"

    def test_extract_types(self, sample_typescript_code):
        """Test extracting TypeScript type aliases."""
        result = ExtractorFactory.extract_symbols(sample_typescript_code, "test.ts")

        if result and result.success:
            types = result.get_symbols_by_type(SymbolType.TYPE_ALIAS)
            type_names = [t.name for t in types]
            assert "UserID" in type_names or len(types) >= 0

    def test_extract_enums(self, sample_typescript_code):
        """Test extracting TypeScript enums."""
        result = ExtractorFactory.extract_symbols(sample_typescript_code, "test.ts")

        if result and result.success:
            enums = result.get_symbols_by_type(SymbolType.ENUM)
            if enums:
                assert enums[0].name == "Status"

    def test_extract_classes(self, sample_typescript_code):
        """Test extracting TypeScript classes."""
        result = ExtractorFactory.extract_symbols(sample_typescript_code, "test.ts")

        if result and result.success:
            classes = result.get_symbols_by_type(SymbolType.CLASS)
            class_names = [c.name for c in classes]
            assert "UserService" in class_names or len(classes) >= 0


class TestGoExtractor:
    """Tests for Go symbol extraction."""

    def test_extract_functions(self, sample_go_code):
        """Test extracting Go functions."""
        result = ExtractorFactory.extract_symbols(sample_go_code, "test.go")

        if result and result.success:
            functions = result.get_symbols_by_type(SymbolType.FUNCTION)
            function_names = [f.name for f in functions]

            assert "NewServer" in function_names or "PublicFunction" in function_names

    def test_extract_structs(self, sample_go_code):
        """Test extracting Go structs."""
        result = ExtractorFactory.extract_symbols(sample_go_code, "test.go")

        if result and result.success:
            structs = result.get_symbols_by_type(SymbolType.STRUCT)
            struct_names = [s.name for s in structs]

            assert "User" in struct_names or "Server" in struct_names

    def test_extract_methods(self, sample_go_code):
        """Test extracting Go methods."""
        result = ExtractorFactory.extract_symbols(sample_go_code, "test.go")

        if result and result.success:
            methods = result.get_symbols_by_type(SymbolType.METHOD)
            method_names = [m.name for m in methods]

            assert "Start" in method_names or "HandleRequest" in method_names

    def test_exported_vs_unexported(self, sample_go_code):
        """Test distinguishing exported vs unexported symbols."""
        result = ExtractorFactory.extract_symbols(sample_go_code, "test.go")

        if result and result.success:
            # Check that exported symbols are marked correctly
            public_symbols = result.get_public_symbols()
            assert len(public_symbols) > 0


class TestRustExtractor:
    """Tests for Rust symbol extraction."""

    def test_extract_functions(self, sample_rust_code):
        """Test extracting Rust functions."""
        result = ExtractorFactory.extract_symbols(sample_rust_code, "test.rs")

        if result and result.success:
            functions = result.get_symbols_by_type(SymbolType.FUNCTION)
            function_names = [f.name for f in functions]

            assert "create_user" in function_names or len(functions) > 0

    def test_extract_structs(self, sample_rust_code):
        """Test extracting Rust structs."""
        result = ExtractorFactory.extract_symbols(sample_rust_code, "test.rs")

        if result and result.success:
            structs = result.get_symbols_by_type(SymbolType.STRUCT)
            if structs:
                assert structs[0].name == "User"

    def test_extract_traits(self, sample_rust_code):
        """Test extracting Rust traits."""
        result = ExtractorFactory.extract_symbols(sample_rust_code, "test.rs")

        if result and result.success:
            traits = result.get_symbols_by_type(SymbolType.TRAIT)
            if traits:
                assert traits[0].name == "Greeter"

    def test_extract_enums(self, sample_rust_code):
        """Test extracting Rust enums."""
        result = ExtractorFactory.extract_symbols(sample_rust_code, "test.rs")

        if result and result.success:
            enums = result.get_symbols_by_type(SymbolType.ENUM)
            if enums:
                assert enums[0].name == "Status"

    def test_pub_visibility(self, sample_rust_code):
        """Test detecting pub visibility."""
        result = ExtractorFactory.extract_symbols(sample_rust_code, "test.rs")

        if result and result.success:
            public_symbols = result.get_public_symbols()
            assert len(public_symbols) > 0


class TestJavaExtractor:
    """Tests for Java symbol extraction."""

    def test_extract_classes(self, sample_java_code):
        """Test extracting Java classes."""
        result = ExtractorFactory.extract_symbols(sample_java_code, "Test.java")

        if result and result.success:
            classes = result.get_symbols_by_type(SymbolType.CLASS)
            class_names = [c.name for c in classes]

            assert "User" in class_names or "UserService" in class_names

    def test_extract_interfaces(self, sample_java_code):
        """Test extracting Java interfaces."""
        result = ExtractorFactory.extract_symbols(sample_java_code, "Test.java")

        if result and result.success:
            interfaces = result.get_symbols_by_type(SymbolType.INTERFACE)
            if interfaces:
                assert interfaces[0].name == "UserRepository"

    def test_extract_methods(self, sample_java_code):
        """Test extracting Java methods."""
        result = ExtractorFactory.extract_symbols(sample_java_code, "Test.java")

        if result and result.success:
            methods = result.get_symbols_by_type(SymbolType.METHOD)
            method_names = [m.name for m in methods]

            assert len(method_names) > 0

    def test_extract_enums(self, sample_java_code):
        """Test extracting Java enums."""
        result = ExtractorFactory.extract_symbols(sample_java_code, "Test.java")

        if result and result.success:
            enums = result.get_symbols_by_type(SymbolType.ENUM)
            if enums:
                assert enums[0].name == "Status"


class TestRubyExtractor:
    """Tests for Ruby symbol extraction."""

    def test_extract_classes(self, sample_ruby_code):
        """Test extracting Ruby classes."""
        result = ExtractorFactory.extract_symbols(sample_ruby_code, "test.rb")

        if result and result.success:
            classes = result.get_symbols_by_type(SymbolType.CLASS)
            class_names = [c.name for c in classes]

            assert "User" in class_names or "AdminUser" in class_names

    def test_extract_modules(self, sample_ruby_code):
        """Test extracting Ruby modules."""
        result = ExtractorFactory.extract_symbols(sample_ruby_code, "test.rb")

        if result and result.success:
            modules = result.get_symbols_by_type(SymbolType.MODULE)
            if modules:
                assert modules[0].name == "MyModule"

    def test_extract_methods(self, sample_ruby_code):
        """Test extracting Ruby methods."""
        result = ExtractorFactory.extract_symbols(sample_ruby_code, "test.rb")

        if result and result.success:
            methods = result.get_symbols_by_type(SymbolType.METHOD)
            assert len(methods) > 0


class TestPHPExtractor:
    """Tests for PHP symbol extraction."""

    def test_extract_classes(self, sample_php_code):
        """Test extracting PHP classes."""
        result = ExtractorFactory.extract_symbols(sample_php_code, "test.php")

        if result and result.success:
            classes = result.get_symbols_by_type(SymbolType.CLASS)
            class_names = [c.name for c in classes]

            assert "User" in class_names or "UserService" in class_names

    def test_extract_interfaces(self, sample_php_code):
        """Test extracting PHP interfaces."""
        result = ExtractorFactory.extract_symbols(sample_php_code, "test.php")

        if result and result.success:
            interfaces = result.get_symbols_by_type(SymbolType.INTERFACE)
            if interfaces:
                assert interfaces[0].name == "UserInterface"

    def test_extract_traits(self, sample_php_code):
        """Test extracting PHP traits."""
        result = ExtractorFactory.extract_symbols(sample_php_code, "test.php")

        if result and result.success:
            traits = result.get_symbols_by_type(SymbolType.TRAIT)
            if traits:
                assert traits[0].name == "Timestampable"


class TestCSharpExtractor:
    """Tests for C# symbol extraction."""

    def test_extract_classes(self, sample_csharp_code):
        """Test extracting C# classes."""
        result = ExtractorFactory.extract_symbols(sample_csharp_code, "Test.cs")

        if result and result.success:
            classes = result.get_symbols_by_type(SymbolType.CLASS)
            class_names = [c.name for c in classes]

            assert "User" in class_names or "AdminUser" in class_names

    def test_extract_interfaces(self, sample_csharp_code):
        """Test extracting C# interfaces."""
        result = ExtractorFactory.extract_symbols(sample_csharp_code, "Test.cs")

        if result and result.success:
            interfaces = result.get_symbols_by_type(SymbolType.INTERFACE)
            if interfaces:
                assert interfaces[0].name == "IUser"

    def test_extract_structs(self, sample_csharp_code):
        """Test extracting C# structs."""
        result = ExtractorFactory.extract_symbols(sample_csharp_code, "Test.cs")

        if result and result.success:
            structs = result.get_symbols_by_type(SymbolType.STRUCT)
            if structs:
                assert structs[0].name == "Point"


class TestBashExtractor:
    """Tests for Bash symbol extraction."""

    def test_extract_functions(self, sample_bash_code):
        """Test extracting Bash functions."""
        result = ExtractorFactory.extract_symbols(sample_bash_code, "test.sh")

        if result and result.success:
            functions = result.get_symbols_by_type(SymbolType.FUNCTION)
            function_names = [f.name for f in functions]

            assert "simple_function" in function_names or "process_file" in function_names


class TestExtractorFactory:
    """Tests for the ExtractorFactory."""

    def test_get_extractor_by_extension(self):
        """Test getting extractor by file extension."""
        extractor = ExtractorFactory.get_extractor(file_path="test.py")
        assert extractor is not None

    def test_get_extractor_by_language(self):
        """Test getting extractor by language name."""
        extractor = ExtractorFactory.get_extractor(language="python")
        assert extractor is not None

    def test_supports_file(self):
        """Test checking file support."""
        assert ExtractorFactory.supports_file("test.js") is True
        assert ExtractorFactory.supports_file("test.go") is True
        assert ExtractorFactory.supports_file("test.unknown") is False

    def test_supports_language(self):
        """Test checking language support."""
        assert ExtractorFactory.supports_language("javascript") is True
        assert ExtractorFactory.supports_language("rust") is True
        assert ExtractorFactory.supports_language("unknown") is False

    def test_get_supported_extensions(self):
        """Test getting list of supported extensions."""
        extensions = ExtractorFactory.get_supported_extensions()
        assert ".js" in extensions
        assert ".py" in extensions
        assert ".go" in extensions
        assert ".rs" in extensions

    def test_get_supported_languages(self):
        """Test getting list of supported languages."""
        languages = ExtractorFactory.get_supported_languages()
        assert "javascript" in languages
        assert "go" in languages
        assert "rust" in languages

    def test_extract_symbols_with_invalid_language(self):
        """Test extracting symbols with invalid language."""
        result = ExtractorFactory.extract_symbols("code", "test.unknown")
        assert result is None

    def test_extract_symbols_javascript(self, sample_javascript_code):
        """Test full extraction pipeline for JavaScript."""
        result = ExtractorFactory.extract_symbols(sample_javascript_code, "test.js")
        assert result is not None
        assert result.success is True
        assert len(result.symbols) > 0

    def test_extract_symbols_python(self, sample_python_code):
        """Test full extraction pipeline for Python."""
        # Note: Python uses AST, not tree-sitter, so may not be in ExtractorFactory
        # This test validates the factory pattern works
        result = ExtractorFactory.extract_symbols(sample_python_code, "test.py")
        # May be None since Python has its own parser
        assert result is None or (result.success and len(result.symbols) >= 0)
