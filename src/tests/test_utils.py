"""
Tests for utility functions in the utils module.

Tests file operations, encoding detection, language detection, and project root detection.
"""

import pytest

from filekitty.core.utils import (
    detect_language,
    detect_project_root,
    is_text_file,
    read_file_contents,
)


class TestIsTextFile:
    """Tests for text file detection."""

    def test_text_file_detection_utf8(self, create_test_file):
        """Test detecting UTF-8 text files."""
        file_path = create_test_file("text.txt", "Hello, World!")
        assert is_text_file(str(file_path)) is True

    def test_text_file_detection_python(self, create_test_file, sample_python_code):
        """Test detecting Python files as text."""
        file_path = create_test_file("test.py", sample_python_code)
        assert is_text_file(str(file_path)) is True

    def test_binary_file_detection(self, create_test_file):
        """Test detecting binary files."""
        # Create a file with null bytes (typical binary indicator)
        binary_content = b"\x00\x01\x02\x03\xFF\xFE"
        file_path = create_test_file("binary.bin", "")
        file_path.write_bytes(binary_content)
        assert is_text_file(str(file_path)) is False

    def test_empty_file_is_text(self, create_test_file):
        """Test that empty files are considered text."""
        file_path = create_test_file("empty.txt", "")
        assert is_text_file(str(file_path)) is True

    def test_nonexistent_file(self):
        """Test handling of nonexistent files."""
        assert is_text_file("/nonexistent/file.txt") is False

    def test_large_text_file(self, create_test_file):
        """Test detecting large text files."""
        large_text = "Line of text\n" * 10000
        file_path = create_test_file("large.txt", large_text)
        assert is_text_file(str(file_path)) is True

    def test_unicode_text_file(self, create_test_file):
        """Test detecting Unicode text files."""
        unicode_text = "Hello 世界! 🌍"
        file_path = create_test_file("unicode.txt", unicode_text)
        assert is_text_file(str(file_path)) is True


class TestReadFileContents:
    """Tests for file content reading with encoding detection."""

    def test_read_utf8_file(self, create_test_file):
        """Test reading UTF-8 encoded file."""
        content = "Hello, World!"
        file_path = create_test_file("test.txt", content)
        assert read_file_contents(str(file_path)) == content

    def test_read_file_with_unicode(self, create_test_file):
        """Test reading file with Unicode characters."""
        content = "Hello 世界! 🌍"
        file_path = create_test_file("unicode.txt", content)
        assert read_file_contents(str(file_path)) == content

    def test_read_multiline_file(self, create_test_file):
        """Test reading multiline file."""
        content = "Line 1\nLine 2\nLine 3"
        file_path = create_test_file("multiline.txt", content)
        assert read_file_contents(str(file_path)) == content

    def test_read_empty_file(self, create_test_file):
        """Test reading empty file."""
        file_path = create_test_file("empty.txt", "")
        assert read_file_contents(str(file_path)) == ""

    def test_read_nonexistent_file(self):
        """Test reading nonexistent file."""
        result = read_file_contents("/nonexistent/file.txt")
        # Should return error message or empty string
        assert isinstance(result, str)

    def test_read_python_file(self, create_test_file, sample_python_code):
        """Test reading Python source file."""
        file_path = create_test_file("test.py", sample_python_code)
        content = read_file_contents(str(file_path))
        assert "import os" in content
        assert "class MyClass:" in content

    def test_read_file_with_different_line_endings(self, create_test_file):
        """Test reading file with different line endings."""
        # Unix style (LF)
        file_path_lf = create_test_file("lf.txt", "")
        file_path_lf.write_bytes(b"Line 1\nLine 2\nLine 3")

        # Windows style (CRLF)
        file_path_crlf = create_test_file("crlf.txt", "")
        file_path_crlf.write_bytes(b"Line 1\r\nLine 2\r\nLine 3")

        content_lf = read_file_contents(str(file_path_lf))
        content_crlf = read_file_contents(str(file_path_crlf))

        # Both should be readable
        assert "Line 1" in content_lf
        assert "Line 1" in content_crlf

    def test_fallback_encoding(self, create_test_file):
        """Test fallback encoding handling."""
        # Create file with Latin-1 encoding
        file_path = create_test_file("latin1.txt", "")
        file_path.write_bytes("Café".encode("latin-1"))

        content = read_file_contents(str(file_path))
        # Should successfully read the file
        assert "Caf" in content


class TestDetectLanguage:
    """Tests for programming language detection."""

    def test_detect_python(self):
        """Test detecting Python files."""
        assert detect_language("test.py") == "python"
        assert detect_language("/path/to/script.py") == "python"

    def test_detect_javascript(self):
        """Test detecting JavaScript files."""
        assert detect_language("app.js") == "javascript"
        assert detect_language("module.mjs") == "javascript"
        assert detect_language("component.jsx") == "javascript"

    def test_detect_typescript(self):
        """Test detecting TypeScript files."""
        assert detect_language("app.ts") == "typescript"
        assert detect_language("component.tsx") == "typescript"

    def test_detect_go(self):
        """Test detecting Go files."""
        assert detect_language("main.go") == "go"

    def test_detect_rust(self):
        """Test detecting Rust files."""
        assert detect_language("main.rs") == "rust"

    def test_detect_java(self):
        """Test detecting Java files."""
        assert detect_language("Main.java") == "java"

    def test_detect_c(self):
        """Test detecting C files."""
        assert detect_language("program.c") == "c"
        assert detect_language("header.h") == "c"

    def test_detect_cpp(self):
        """Test detecting C++ files."""
        assert detect_language("program.cpp") == "cpp"
        assert detect_language("header.hpp") == "cpp"
        assert detect_language("file.cc") == "cpp"
        assert detect_language("file.cxx") == "cpp"

    def test_detect_ruby(self):
        """Test detecting Ruby files."""
        assert detect_language("script.rb") == "ruby"

    def test_detect_php(self):
        """Test detecting PHP files."""
        assert detect_language("index.php") == "php"

    def test_detect_shell(self):
        """Test detecting shell scripts."""
        assert detect_language("script.sh") == "sh"
        assert detect_language("script.bash") == "bash"

    def test_detect_markdown(self):
        """Test detecting Markdown files."""
        assert detect_language("README.md") == "markdown"

    def test_detect_json(self):
        """Test detecting JSON files."""
        assert detect_language("package.json") == "json"

    def test_detect_yaml(self):
        """Test detecting YAML files."""
        assert detect_language("config.yaml") == "yaml"
        assert detect_language("config.yml") == "yaml"

    def test_detect_sql(self):
        """Test detecting SQL files."""
        assert detect_language("schema.sql") == "sql"

    def test_detect_html(self):
        """Test detecting HTML files."""
        assert detect_language("index.html") == "html"

    def test_detect_css(self):
        """Test detecting CSS files."""
        assert detect_language("style.css") == "css"

    def test_detect_unknown_extension(self):
        """Test detecting unknown file extensions."""
        result = detect_language("file.unknown")
        assert result is None or result == ""

    def test_detect_no_extension(self):
        """Test detecting files without extension."""
        result = detect_language("Makefile")
        assert result is None or result == ""

    def test_case_insensitive_detection(self):
        """Test case-insensitive language detection."""
        assert detect_language("Test.PY") == "python"
        assert detect_language("App.JS") == "javascript"


class TestDetectProjectRoot:
    """Tests for project root detection."""

    def test_detect_python_project_with_pyproject(self, temp_dir):
        """Test detecting Python project with pyproject.toml."""
        (temp_dir / "pyproject.toml").write_text("[tool.poetry]")
        file_path = temp_dir / "src" / "module.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("# Python code")

        root = detect_project_root(str(file_path))
        assert root == str(temp_dir)

    def test_detect_python_project_with_setup_py(self, temp_dir):
        """Test detecting Python project with setup.py."""
        (temp_dir / "setup.py").write_text("from setuptools import setup")
        file_path = temp_dir / "src" / "module.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("# Python code")

        root = detect_project_root(str(file_path))
        assert root == str(temp_dir)

    def test_detect_python_project_with_requirements(self, temp_dir):
        """Test detecting Python project with requirements.txt."""
        (temp_dir / "requirements.txt").write_text("pytest>=7.0")
        file_path = temp_dir / "src" / "module.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("# Python code")

        root = detect_project_root(str(file_path))
        assert root == str(temp_dir)

    def test_detect_nodejs_project(self, temp_dir):
        """Test detecting Node.js project with package.json."""
        (temp_dir / "package.json").write_text('{"name": "myapp"}')
        file_path = temp_dir / "src" / "app.js"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("console.log('hello');")

        root = detect_project_root(str(file_path))
        assert root == str(temp_dir)

    def test_detect_rust_project(self, temp_dir):
        """Test detecting Rust project with Cargo.toml."""
        (temp_dir / "Cargo.toml").write_text('[package]\nname = "myapp"')
        file_path = temp_dir / "src" / "main.rs"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("fn main() {}")

        root = detect_project_root(str(file_path))
        assert root == str(temp_dir)

    def test_detect_java_maven_project(self, temp_dir):
        """Test detecting Java Maven project with pom.xml."""
        (temp_dir / "pom.xml").write_text("<project></project>")
        file_path = temp_dir / "src" / "main" / "java" / "App.java"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("class App {}")

        root = detect_project_root(str(file_path))
        assert root == str(temp_dir)

    def test_detect_java_gradle_project(self, temp_dir):
        """Test detecting Java Gradle project with build.gradle."""
        (temp_dir / "build.gradle").write_text("plugins {}")
        file_path = temp_dir / "src" / "main" / "java" / "App.java"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("class App {}")

        root = detect_project_root(str(file_path))
        assert root == str(temp_dir)

    def test_detect_git_repository(self, temp_dir):
        """Test detecting Git repository root."""
        (temp_dir / ".git").mkdir()
        file_path = temp_dir / "src" / "code.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("# Code")

        root = detect_project_root(str(file_path))
        assert root == str(temp_dir)

    def test_no_project_root_found(self, temp_dir):
        """Test when no project root markers are found."""
        file_path = temp_dir / "random" / "file.txt"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("Random content")

        root = detect_project_root(str(file_path))
        # Should return None or the file's directory
        assert root is None or root == str(file_path.parent)

    def test_nested_project_detection(self, temp_dir):
        """Test detection in deeply nested directory structure."""
        root_marker = temp_dir / "pyproject.toml"
        root_marker.write_text("[tool.poetry]")

        nested_file = temp_dir / "a" / "b" / "c" / "d" / "file.py"
        nested_file.parent.mkdir(parents=True)
        nested_file.write_text("# Code")

        root = detect_project_root(str(nested_file))
        assert root == str(temp_dir)

    def test_nonexistent_file(self):
        """Test project root detection for nonexistent file."""
        root = detect_project_root("/nonexistent/path/file.py")
        assert root is None
