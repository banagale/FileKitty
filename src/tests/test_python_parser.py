"""
Tests for Python AST parser and code extraction.

Tests the python_parser module which provides Python-specific symbol extraction
using the built-in ast module.
"""

import pytest

from filekitty.core.python_parser import (
    CodeExtractor,
    SymbolVisitor,
    extract_code_and_imports,
    parse_python_file,
)


class TestSymbolVisitor:
    """Tests for the SymbolVisitor AST visitor."""

    def test_extract_classes_from_code(self, sample_python_code, create_test_file):
        """Test extracting class names from Python code."""
        file_path = create_test_file("test.py", sample_python_code)
        classes, _, _, _ = parse_python_file(str(file_path))

        assert "MyClass" in classes
        assert "AnotherClass" in classes
        assert len(classes) == 2

    def test_extract_functions_from_code(self, sample_python_code, create_test_file):
        """Test extracting function names from Python code."""
        file_path = create_test_file("test.py", sample_python_code)
        _, functions, _, _ = parse_python_file(str(file_path))

        assert "my_function" in functions
        assert "async_function" in functions
        assert "_private_function" in functions
        assert len(functions) == 3

    def test_extract_imports(self, sample_python_code, create_test_file):
        """Test extracting import statements."""
        file_path = create_test_file("test.py", sample_python_code)
        _, _, imports, _ = parse_python_file(str(file_path))

        assert "import os" in imports
        assert "import sys" in imports
        assert "from pathlib import Path" in imports
        assert len(imports) == 3

    def test_extract_import_mapping(self, sample_python_code, create_test_file):
        """Test extracting imported names mapping."""
        file_path = create_test_file("test.py", sample_python_code)
        _, _, _, imported_names = parse_python_file(str(file_path))

        assert "os" in imported_names
        assert "sys" in imported_names
        assert "Path" in imported_names
        assert imported_names["Path"] == "pathlib"

    def test_parse_file_with_syntax_error(self, create_test_file):
        """Test parsing file with syntax errors."""
        bad_code = "def bad_function(\n    # Missing closing paren"
        file_path = create_test_file("bad.py", bad_code)

        classes, functions, imports, imported_names = parse_python_file(str(file_path))

        # Should return empty results, not crash
        assert classes == []
        assert functions == []
        assert imports == []
        assert imported_names == {}

    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist."""
        classes, functions, imports, imported_names = parse_python_file("/nonexistent/file.py")

        assert classes == []
        assert functions == []
        assert imports == []
        assert imported_names == {}

    def test_parse_empty_file(self, create_test_file):
        """Test parsing an empty Python file."""
        file_path = create_test_file("empty.py", "")

        classes, functions, imports, imported_names = parse_python_file(str(file_path))

        assert classes == []
        assert functions == []
        assert imports == []
        assert imported_names == {}

    def test_parse_file_with_only_imports(self, create_test_file):
        """Test parsing file with only import statements."""
        code = "import os\nimport sys\nfrom pathlib import Path"
        file_path = create_test_file("imports.py", code)

        classes, functions, imports, imported_names = parse_python_file(str(file_path))

        assert classes == []
        assert functions == []
        assert len(imports) == 3
        assert len(imported_names) == 3

    def test_nested_class_extraction(self, create_test_file):
        """Test extracting nested classes."""
        code = """
class Outer:
    class Inner:
        pass
"""
        file_path = create_test_file("nested.py", code)
        classes, _, _, _ = parse_python_file(str(file_path))

        # Should extract both outer and inner classes
        assert "Outer" in classes
        assert "Inner" in classes

    def test_method_vs_function_distinction(self, create_test_file):
        """Test that methods are not counted as functions."""
        code = """
class MyClass:
    def my_method(self):
        pass

def my_function():
    pass
"""
        file_path = create_test_file("methods.py", code)
        classes, functions, _, _ = parse_python_file(str(file_path))

        assert "MyClass" in classes
        assert "my_function" in functions
        assert "my_method" not in functions


class TestCodeExtractor:
    """Tests for the CodeExtractor AST visitor."""

    def test_extract_single_function(self, sample_python_code, create_test_file):
        """Test extracting a single function with imports."""
        file_path = create_test_file("test.py", sample_python_code)
        selected_items = ["my_function"]

        result = extract_code_and_imports(
            sample_python_code,
            selected_items,
            str(file_path),
            f"Modified: (not available)"
        )

        assert "def my_function(x, y):" in result
        assert "Function docstring." in result
        assert "return x + y" in result

    def test_extract_single_class(self, sample_python_code, create_test_file):
        """Test extracting a single class."""
        file_path = create_test_file("test.py", sample_python_code)
        selected_items = ["MyClass"]

        result = extract_code_and_imports(
            sample_python_code,
            selected_items,
            str(file_path),
            f"Modified: (not available)"
        )

        assert "class MyClass:" in result
        assert "Class docstring." in result
        assert "def __init__(self):" in result
        assert "def my_method(self, arg):" in result

    def test_extract_multiple_symbols(self, sample_python_code, create_test_file):
        """Test extracting multiple symbols at once."""
        file_path = create_test_file("test.py", sample_python_code)
        selected_items = ["MyClass", "my_function"]

        result = extract_code_and_imports(
            sample_python_code,
            selected_items,
            str(file_path),
            f"Modified: (not available)"
        )

        assert "class MyClass:" in result
        assert "def my_function(x, y):" in result

    def test_extract_with_necessary_imports(self, create_test_file):
        """Test that necessary imports are included."""
        code = """
import os
from pathlib import Path

def use_path():
    return Path("/tmp")
"""
        file_path = create_test_file("imports.py", code)
        selected_items = ["use_path"]

        result = extract_code_and_imports(
            code,
            selected_items,
            str(file_path),
            f"Modified: (not available)"
        )

        # Should include the import since the function uses Path
        assert "from pathlib import Path" in result
        assert "def use_path():" in result

    def test_extract_inherited_class(self, sample_python_code, create_test_file):
        """Test extracting a class that inherits from another."""
        file_path = create_test_file("test.py", sample_python_code)
        selected_items = ["AnotherClass"]

        result = extract_code_and_imports(
            sample_python_code,
            selected_items,
            str(file_path),
            f"Modified: (not available)"
        )

        assert "class AnotherClass(MyClass):" in result

    def test_extract_async_function(self, sample_python_code, create_test_file):
        """Test extracting async function."""
        file_path = create_test_file("test.py", sample_python_code)
        selected_items = ["async_function"]

        result = extract_code_and_imports(
            sample_python_code,
            selected_items,
            str(file_path),
            f"Modified: (not available)"
        )

        assert "async def async_function():" in result

    def test_extract_nonexistent_symbol(self, sample_python_code, create_test_file):
        """Test extracting a symbol that doesn't exist."""
        file_path = create_test_file("test.py", sample_python_code)
        selected_items = ["NonexistentClass"]

        result = extract_code_and_imports(
            sample_python_code,
            selected_items,
            str(file_path),
            f"Modified: (not available)"
        )

        # Should not crash, might return message or empty result
        assert isinstance(result, str)

    def test_preserve_docstrings(self, sample_python_code, create_test_file):
        """Test that docstrings are preserved in extracted code."""
        file_path = create_test_file("test.py", sample_python_code)
        selected_items = ["MyClass"]

        result = extract_code_and_imports(
            sample_python_code,
            selected_items,
            str(file_path),
            f"Modified: (not available)"
        )

        assert '"""Class docstring."""' in result
        assert '"""Method docstring."""' in result

    def test_preserve_indentation(self, sample_python_code, create_test_file):
        """Test that indentation is preserved correctly."""
        file_path = create_test_file("test.py", sample_python_code)
        selected_items = ["MyClass"]

        result = extract_code_and_imports(
            sample_python_code,
            selected_items,
            str(file_path),
            f"Modified: (not available)"
        )

        # Check that method is properly indented under class
        lines = result.split("\n")
        class_line_idx = next(i for i, line in enumerate(lines) if "class MyClass:" in line)
        method_line_idx = next(i for i, line in enumerate(lines) if "def __init__(self):" in line)

        # Method should be indented relative to class
        assert lines[method_line_idx].startswith("    def")

    def test_extract_with_decorators(self, create_test_file):
        """Test extracting functions/methods with decorators."""
        code = """
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_function(x):
    return x * 2

class MyClass:
    @property
    def my_property(self):
        return self._value

    @staticmethod
    def static_method():
        return "static"
"""
        file_path = create_test_file("decorators.py", code)
        selected_items = ["cached_function", "MyClass"]

        result = extract_code_and_imports(
            code,
            selected_items,
            str(file_path),
            f"Modified: (not available)"
        )

        assert "@lru_cache(maxsize=128)" in result
        assert "@property" in result
        assert "@staticmethod" in result
