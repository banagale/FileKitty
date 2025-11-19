"""
Integration tests for FileKitty's file processing pipeline.

Tests the complete workflow from file selection to output generation.
"""

import pytest
from pathlib import Path

from filekitty.core.utils import detect_project_root, is_text_file, read_file_contents
from filekitty.core.python_parser import parse_python_file, extract_code_and_imports
from filekitty.core.project_tree import generate_tree
from filekitty.core.extractor_factory import ExtractorFactory


class TestFileProcessingPipeline:
    """Tests for the complete file processing pipeline."""

    def test_python_file_pipeline(self, create_test_file, sample_python_code, temp_dir):
        """Test complete pipeline for Python file processing."""
        # 1. Create test file
        file_path = create_test_file("test.py", sample_python_code)

        # 2. Verify file is text
        assert is_text_file(str(file_path)) is True

        # 3. Read file contents
        content = read_file_contents(str(file_path))
        assert "class MyClass:" in content

        # 4. Parse Python symbols
        classes, functions, imports, imported_names = parse_python_file(str(file_path))
        assert "MyClass" in classes
        assert "my_function" in functions

        # 5. Extract specific code
        extracted = extract_code_and_imports(
            content,
            ["MyClass"],
            str(file_path),
            "Modified: 2024-01-01"
        )
        assert "class MyClass:" in extracted

    def test_multi_language_pipeline(self, create_test_file, sample_javascript_code, sample_go_code):
        """Test pipeline with multiple languages."""
        # Create files in different languages
        js_file = create_test_file("app.js", sample_javascript_code)
        go_file = create_test_file("main.go", sample_go_code)

        # Process JavaScript
        if is_text_file(str(js_file)):
            js_content = read_file_contents(str(js_file))
            js_result = ExtractorFactory.extract_symbols(js_content, str(js_file))
            if js_result and js_result.success:
                assert len(js_result.symbols) > 0

        # Process Go
        if is_text_file(str(go_file)):
            go_content = read_file_contents(str(go_file))
            go_result = ExtractorFactory.extract_symbols(go_content, str(go_file))
            if go_result and go_result.success:
                assert len(go_result.symbols) > 0

    def test_project_tree_generation(self, temp_dir, create_test_file, sample_python_code):
        """Test generating project tree."""
        # Create project structure
        (temp_dir / "src").mkdir()
        (temp_dir / "tests").mkdir()

        create_test_file("src/main.py", sample_python_code)
        create_test_file("src/utils.py", "def helper(): pass")
        create_test_file("tests/test_main.py", sample_python_code)
        create_test_file("README.md", "# Project")

        # Generate tree
        tree_output = generate_tree(str(temp_dir), ignore_regex=r"\.git|__pycache__|\.pyc$")

        assert tree_output is not None
        assert "src" in tree_output
        assert "tests" in tree_output

    def test_project_root_detection_pipeline(self, temp_dir, create_test_file):
        """Test project root detection in pipeline."""
        # Create project structure with marker
        (temp_dir / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")
        (temp_dir / "src" / "package").mkdir(parents=True)

        file_path = create_test_file("src/package/module.py", "# Code")

        # Detect project root
        root = detect_project_root(str(file_path))
        assert root == str(temp_dir)

    def test_error_handling_pipeline(self, create_test_file):
        """Test error handling in the pipeline."""
        # Create file with syntax error
        bad_file = create_test_file("bad.py", "def bad(\n  # Invalid")

        # Should handle gracefully
        content = read_file_contents(str(bad_file))
        assert isinstance(content, str)

        classes, functions, _, _ = parse_python_file(str(bad_file))
        # Should return empty results, not crash
        assert classes == []
        assert functions == []

    def test_encoding_handling_pipeline(self, create_test_file):
        """Test handling different file encodings."""
        # Create file with Unicode
        unicode_file = create_test_file("unicode.py", "# -*- coding: utf-8 -*-\n# Comment with emoji: 🎉\n")

        assert is_text_file(str(unicode_file)) is True
        content = read_file_contents(str(unicode_file))
        assert "🎉" in content

    def test_large_file_pipeline(self, create_test_file):
        """Test processing large files."""
        # Generate large Python file
        large_code = "# Header\n"
        for i in range(100):
            large_code += f"def function_{i}(): pass\n"
        for i in range(50):
            large_code += f"class Class_{i}: pass\n"

        large_file = create_test_file("large.py", large_code)

        assert is_text_file(str(large_file)) is True
        content = read_file_contents(str(large_file))
        assert len(content) > 1000

        classes, functions, _, _ = parse_python_file(str(large_file))
        assert len(classes) == 50
        assert len(functions) == 100


class TestCrossLanguageIntegration:
    """Tests for cross-language integration scenarios."""

    def test_mixed_language_project(self, temp_dir, create_test_file, sample_python_code,
                                    sample_javascript_code, sample_rust_code):
        """Test processing a project with multiple languages."""
        # Create multi-language project
        (temp_dir / "backend").mkdir()
        (temp_dir / "frontend").mkdir()

        backend_file = create_test_file("backend/api.py", sample_python_code)
        frontend_file = create_test_file("frontend/app.js", sample_javascript_code)
        lib_file = create_test_file("backend/lib.rs", sample_rust_code)

        # Process all files
        files_processed = 0
        total_symbols = 0

        for file_path in [backend_file, frontend_file, lib_file]:
            if is_text_file(str(file_path)):
                content = read_file_contents(str(file_path))
                result = ExtractorFactory.extract_symbols(content, str(file_path))

                if result and result.success:
                    files_processed += 1
                    total_symbols += len(result.symbols)

        assert files_processed > 0
        assert total_symbols > 0

    def test_export_detection_across_languages(self, sample_go_code, sample_rust_code,
                                               sample_typescript_code):
        """Test detecting exported symbols across languages."""
        # Go: Uppercase = exported
        go_result = ExtractorFactory.extract_symbols(sample_go_code, "test.go")
        if go_result and go_result.success:
            go_public = go_result.get_public_symbols()
            assert len(go_public) > 0

        # Rust: pub = exported
        rust_result = ExtractorFactory.extract_symbols(sample_rust_code, "test.rs")
        if rust_result and rust_result.success:
            rust_public = rust_result.get_public_symbols()
            assert len(rust_public) > 0

        # TypeScript: export = exported
        ts_result = ExtractorFactory.extract_symbols(sample_typescript_code, "test.ts")
        if ts_result and ts_result.success:
            ts_public = ts_result.get_public_symbols()
            assert len(ts_public) > 0


class TestEndToEndScenarios:
    """End-to-end scenario tests."""

    def test_prepare_llm_context_scenario(self, temp_dir, create_test_file,
                                         sample_python_code, sample_javascript_code):
        """Test preparing context for LLM (main use case)."""
        # Setup: User has project with multiple files
        (temp_dir / "pyproject.toml").write_text("[tool.poetry]\nname = 'myapp'")

        backend = create_test_file("backend.py", sample_python_code)
        frontend = create_test_file("frontend.js", sample_javascript_code)
        readme = create_test_file("README.md", "# My App\n\nDescription")

        files_to_process = [str(backend), str(frontend), str(readme)]

        # Step 1: Detect project root
        project_root = detect_project_root(str(backend))
        assert project_root == str(temp_dir)

        # Step 2: Generate project tree
        tree = generate_tree(project_root)
        assert tree is not None

        # Step 3: Extract symbols from code files
        all_symbols = []
        for file_path in files_to_process:
            if is_text_file(file_path) and ExtractorFactory.supports_file(file_path):
                content = read_file_contents(file_path)
                result = ExtractorFactory.extract_symbols(content, file_path)
                if result and result.success:
                    all_symbols.extend(result.symbols)

        # Verify we extracted symbols
        assert len(all_symbols) > 0

    def test_code_review_scenario(self, create_test_file, sample_python_code):
        """Test code review scenario - extract specific symbols."""
        file_path = create_test_file("module.py", sample_python_code)

        # Parse file to see all symbols
        classes, functions, _, _ = parse_python_file(str(file_path))

        # User selects specific class to review
        selected_symbol = "MyClass"
        assert selected_symbol in classes

        # Extract just that symbol
        content = read_file_contents(str(file_path))
        extracted = extract_code_and_imports(
            content,
            [selected_symbol],
            str(file_path),
            "Modified: Today"
        )

        # Verify extraction
        assert "class MyClass:" in extracted
        assert "def my_method" in extracted

    def test_documentation_generation_scenario(self, create_test_file, sample_python_code):
        """Test documentation generation scenario."""
        file_path = create_test_file("api.py", sample_python_code)

        # Extract all public symbols
        classes, functions, _, _ = parse_python_file(str(file_path))

        # Filter out private symbols (starting with _)
        public_functions = [f for f in functions if not f.startswith("_")]
        public_classes = [c for c in classes if not c.startswith("_")]

        # Verify we identified public API
        assert "my_function" in public_functions
        assert "_private_function" not in public_functions
        assert "MyClass" in public_classes
