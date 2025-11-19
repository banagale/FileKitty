"""
Output generation service for FileKitty.

This service handles the generation of formatted output text from selected files,
including tree visualization, file contents, and symbol extraction.

Refactored from main_window.py (lines 644-754) to separate business logic from UI.
"""

from datetime import datetime
from pathlib import Path
from typing import Protocol

from filekitty.core.python_parser import extract_code_and_imports
from filekitty.core.utils import detect_language, display_path, read_file_contents


class TreeGenerator(Protocol):
    """Protocol for tree generation functionality."""

    def generate(
        self, base_path: str, base_path_display: str | None = None, ignore_regex: str = ""
    ) -> tuple[str, str, str]:
        """Generate a tree visualization of the directory structure."""
        ...


class OutputGenerator:
    """
    Service responsible for generating formatted output from selected files.

    This class encapsulates the business logic for:
    - Combining multiple files into a single formatted output
    - Generating project tree visualizations
    - Extracting and formatting code symbols
    - Handling different file types and languages
    """

    def __init__(self, tree_generator: TreeGenerator | None = None):
        """
        Initialize the output generator.

        Args:
            tree_generator: Optional tree generator instance for directory visualization
        """
        self._tree_generator = tree_generator

    def generate_output(
        self,
        files: list[str],
        *,
        project_root: Path | None = None,
        tree_snapshot: dict | None = None,
        selection_mode: str = "All Files",
        selected_file: str | None = None,
        selected_items: list[str] | None = None,
        include_tree: bool = True,
        output_ignore_filter=None,
    ) -> str:
        """
        Generate formatted output from the given files.

        Args:
            files: List of file paths to process
            project_root: Optional project root directory
            tree_snapshot: Optional cached tree visualization
            selection_mode: "All Files" or "Single File"
            selected_file: Path to selected file (for Single File mode)
            selected_items: List of symbols to extract (classes/functions)
            include_tree: Whether to include directory tree visualization
            output_ignore_filter: Optional function to filter out files from output

        Returns:
            Formatted string containing all file contents and metadata
        """
        parts = []
        selected_items = selected_items or []

        # Add project tree if enabled
        if include_tree and tree_snapshot:
            tree_output = self._format_tree_section(tree_snapshot)
            if tree_output:
                parts.append(tree_output)

        # Determine which files to process
        files_to_process = self._get_files_to_process(
            files,
            selection_mode=selection_mode,
            selected_file=selected_file,
            output_ignore_filter=output_ignore_filter,
        )

        # Process each file
        for file_path in files_to_process:
            file_output = self._process_file(
                file_path,
                selected_items=selected_items,
                selection_mode=selection_mode,
                selected_file=selected_file,
            )
            if file_output:
                parts.append(file_output)

        return "\n\n".join(parts)

    def _format_tree_section(self, tree_snapshot: dict) -> str:
        """
        Format the tree visualization section.

        Args:
            tree_snapshot: Dictionary containing tree metadata and rendered output

        Returns:
            Formatted tree section string
        """
        base_path_display = tree_snapshot.get("base_path_display", "")
        rendered = tree_snapshot.get("rendered", "")

        parts = [
            f"Folder Tree: {base_path_display}",
            "```",
            rendered.rstrip(),
            "```",
        ]
        return "\n".join(parts)

    def _get_files_to_process(
        self,
        files: list[str],
        *,
        selection_mode: str,
        selected_file: str | None,
        output_ignore_filter=None,
    ) -> list[str]:
        """
        Determine which files should be processed based on selection mode and filters.

        Args:
            files: All available files
            selection_mode: "All Files" or "Single File"
            selected_file: Selected file path for Single File mode
            output_ignore_filter: Optional filter function

        Returns:
            List of file paths to process
        """
        # Handle single file mode
        if selection_mode == "Single File" and selected_file:
            return [selected_file]

        # Handle all files mode with filtering
        if output_ignore_filter:
            return [f for f in files if not output_ignore_filter(f)]

        return files

    def _process_file(
        self,
        file_path: str,
        *,
        selected_items: list[str],
        selection_mode: str,
        selected_file: str | None,
    ) -> str:
        """
        Process a single file and generate formatted output.

        Args:
            file_path: Path to the file to process
            selected_items: List of symbols to extract (for Python files)
            selection_mode: Current selection mode
            selected_file: Currently selected file

        Returns:
            Formatted file content string
        """
        file_content = read_file_contents(file_path)
        if not file_content:
            return ""

        # Get file metadata
        display_file_path = display_path(file_path)
        language = detect_language(file_path) or ""

        try:
            modified_time = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
            modified_line = f"Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}"
        except (OSError, ValueError):
            modified_line = "Modified: (not available)"

        # Handle Python files with symbol selection
        if language == "python" and selected_items and selection_mode == "Single File":
            if selected_file == file_path:
                # Extract specific symbols
                file_content = extract_code_and_imports(
                    file_content, selected_items, file_path, modified_line
                )
                return self._format_code_block(display_file_path, modified_line, file_content, language)

        # Handle regular files
        return self._format_code_block(display_file_path, modified_line, file_content, language)

    def _format_code_block(
        self,
        file_path: str,
        modified_line: str,
        content: str,
        language: str,
    ) -> str:
        """
        Format a code block with metadata header.

        Args:
            file_path: Display path for the file
            modified_line: Modification timestamp string
            content: File content
            language: Programming language for syntax highlighting

        Returns:
            Formatted code block string
        """
        parts = [
            f"File: {file_path}",
            modified_line,
            f"```{language}",
            content.rstrip(),
            "```",
        ]
        return "\n".join(parts)


class LLMTimestampFormatter:
    """
    Formatter for LLM-friendly timestamp output.

    Provides alternative timestamp formatting optimized for LLM consumption.
    """

    @staticmethod
    def format_timestamp(dt: datetime | None = None) -> str:
        """
        Format a timestamp in a format optimized for LLMs.

        Args:
            dt: Datetime object to format (defaults to now)

        Returns:
            Formatted timestamp string
        """
        if dt is None:
            dt = datetime.now()

        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    @staticmethod
    def format_with_relative(dt: datetime) -> str:
        """
        Format with both absolute and relative time.

        Args:
            dt: Datetime to format

        Returns:
            String with both formats
        """
        now = datetime.now()
        delta = now - dt

        if delta.total_seconds() < 60:
            relative = "just now"
        elif delta.total_seconds() < 3600:
            minutes = int(delta.total_seconds() / 60)
            relative = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            relative = f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(delta.total_seconds() / 86400)
            relative = f"{days} day{'s' if days != 1 else ''} ago"

        absolute = dt.strftime("%Y-%m-%d %H:%M:%S")
        return f"{absolute} ({relative})"
