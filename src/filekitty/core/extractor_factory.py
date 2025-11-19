"""
Factory for creating language-specific symbol extractors.

This module provides a unified API for accessing symbol extractors
across all supported programming languages.
"""

from pathlib import Path
from typing import Any

from filekitty.core.extractors_extended import (
    BashExtractor,
    CExtractor,
    CppExtractor,
    CSharpExtractor,
    JavaExtractor,
    PHPExtractor,
    RubyExtractor,
    RustExtractor,
)
from filekitty.core.symbol_models import ExtractionResult
from filekitty.core.universal_extractor import BaseExtractor, GoExtractor, JavaScriptExtractor


class ExtractorFactory:
    """Factory for creating language-specific symbol extractors."""

    # Map file extensions to extractor classes
    EXTRACTOR_MAP: dict[str, type[BaseExtractor]] = {
        # JavaScript/TypeScript
        ".js": lambda: JavaScriptExtractor(is_typescript=False),
        ".mjs": lambda: JavaScriptExtractor(is_typescript=False),
        ".cjs": lambda: JavaScriptExtractor(is_typescript=False),
        ".jsx": lambda: JavaScriptExtractor(is_typescript=False),
        ".ts": lambda: JavaScriptExtractor(is_typescript=True),
        ".tsx": lambda: JavaScriptExtractor(is_typescript=True),
        ".mts": lambda: JavaScriptExtractor(is_typescript=True),
        ".cts": lambda: JavaScriptExtractor(is_typescript=True),
        # Go
        ".go": GoExtractor,
        # Rust
        ".rs": RustExtractor,
        # Java
        ".java": JavaExtractor,
        # C/C++
        ".c": CExtractor,
        ".h": CExtractor,
        ".cpp": CppExtractor,
        ".cxx": CppExtractor,
        ".cc": CppExtractor,
        ".hpp": CppExtractor,
        ".hxx": CppExtractor,
        ".hh": CppExtractor,
        # Ruby
        ".rb": RubyExtractor,
        # PHP
        ".php": PHPExtractor,
        # C#
        ".cs": CSharpExtractor,
        # Bash
        ".sh": BashExtractor,
        ".bash": BashExtractor,
        ".zsh": BashExtractor,
    }

    # Map language names to extractor classes
    LANGUAGE_MAP: dict[str, type[BaseExtractor]] = {
        "javascript": lambda: JavaScriptExtractor(is_typescript=False),
        "typescript": lambda: JavaScriptExtractor(is_typescript=True),
        "go": GoExtractor,
        "rust": RustExtractor,
        "java": JavaExtractor,
        "c": CExtractor,
        "cpp": CppExtractor,
        "c++": CppExtractor,
        "ruby": RubyExtractor,
        "php": PHPExtractor,
        "csharp": CSharpExtractor,
        "c#": CSharpExtractor,
        "bash": BashExtractor,
        "shell": BashExtractor,
    }

    @classmethod
    def get_extractor(cls, file_path: str | None = None, language: str | None = None) -> BaseExtractor | None:
        """
        Get an appropriate extractor for a file or language.

        Args:
            file_path: Path to the file (used to determine language from extension)
            language: Explicit language name

        Returns:
            BaseExtractor instance or None if no extractor found
        """
        # Try to get extractor by language name
        if language:
            lang_lower = language.lower()
            if lang_lower in cls.LANGUAGE_MAP:
                extractor_class = cls.LANGUAGE_MAP[lang_lower]
                return extractor_class() if callable(extractor_class) else None

        # Try to get extractor by file extension
        if file_path:
            ext = Path(file_path).suffix.lower()
            if ext in cls.EXTRACTOR_MAP:
                extractor_class = cls.EXTRACTOR_MAP[ext]
                return extractor_class() if callable(extractor_class) else None

        return None

    @classmethod
    def extract_symbols(cls, code: str, file_path: str, language: str | None = None) -> ExtractionResult | None:
        """
        Extract symbols from code using the appropriate extractor.

        Args:
            code: Source code as string
            file_path: Path to the source file
            language: Optional explicit language name

        Returns:
            ExtractionResult or None if no suitable extractor found
        """
        extractor = cls.get_extractor(file_path=file_path, language=language)
        if extractor:
            return extractor.extract_symbols(code, file_path)
        return None

    @classmethod
    def supports_language(cls, language: str) -> bool:
        """Check if a language is supported."""
        return language.lower() in cls.LANGUAGE_MAP

    @classmethod
    def supports_file(cls, file_path: str) -> bool:
        """Check if a file extension is supported."""
        ext = Path(file_path).suffix.lower()
        return ext in cls.EXTRACTOR_MAP

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """Get list of all supported file extensions."""
        return list(cls.EXTRACTOR_MAP.keys())

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Get list of all supported language names."""
        return list(cls.LANGUAGE_MAP.keys())


def extract_symbols_from_file(file_path: str, language: str | None = None) -> ExtractionResult | None:
    """
    Convenience function to extract symbols from a file.

    Args:
        file_path: Path to the source file
        language: Optional explicit language name

    Returns:
        ExtractionResult or None if file couldn't be read or parsed
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        return ExtractorFactory.extract_symbols(code, file_path, language)
    except Exception:
        return None


def extract_symbols_from_code(
    code: str, file_path: str = "<string>", language: str | None = None
) -> ExtractionResult | None:
    """
    Convenience function to extract symbols from code string.

    Args:
        code: Source code as string
        file_path: Virtual file path (defaults to "<string>")
        language: Optional explicit language name

    Returns:
        ExtractionResult or None if parsing failed
    """
    return ExtractorFactory.extract_symbols(code, file_path, language)
