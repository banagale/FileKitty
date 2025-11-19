"""
File management service for FileKitty.

This service handles file selection, filtering, and organization,
separating file management logic from UI code.

Refactored from main_window.py to provide a clean service interface.
"""

import os
from pathlib import Path

from filekitty.core.utils import detect_project_root, is_text_file


class FileFilter:
    """Handles file filtering logic."""

    def __init__(self, ignore_pattern_func=None):
        """
        Initialize file filter.

        Args:
            ignore_pattern_func: Optional function that returns True if file should be ignored
        """
        self._ignore_pattern_func = ignore_pattern_func

    def should_include(self, file_path: str) -> bool:
        """
        Determine if a file should be included.

        Args:
            file_path: Path to check

        Returns:
            True if file should be included
        """
        if not self._ignore_pattern_func:
            return True

        return not self._ignore_pattern_func(file_path)

    def filter_files(self, files: list[str]) -> list[str]:
        """
        Filter a list of files.

        Args:
            files: List of file paths

        Returns:
            Filtered list of file paths
        """
        return [f for f in files if self.should_include(f)]


class FileManager:
    """
    Manages file selection, organization, and metadata.

    This service provides functionality for:
    - Selecting files from dialogs
    - Processing dropped files/directories
    - Detecting project roots
    - Managing file collections
    """

    def __init__(self):
        """Initialize the file manager."""
        self._current_files: list[str] = []
        self._project_root: Path | None = None

    @property
    def current_files(self) -> list[str]:
        """Get the current list of files."""
        return self._current_files.copy()

    @property
    def project_root(self) -> Path | None:
        """Get the detected project root."""
        return self._project_root

    def set_files(self, files: list[str]) -> None:
        """
        Set the current file list and detect project root.

        Args:
            files: List of file paths
        """
        self._current_files = list(files)
        self._detect_project_root()

    def add_files(self, files: list[str]) -> None:
        """
        Add files to the current collection.

        Args:
            files: List of file paths to add
        """
        # Deduplicate
        existing = set(self._current_files)
        new_files = [f for f in files if f not in existing]
        self._current_files.extend(new_files)
        self._detect_project_root()

    def remove_file(self, file_path: str) -> bool:
        """
        Remove a file from the collection.

        Args:
            file_path: Path to remove

        Returns:
            True if file was removed
        """
        if file_path in self._current_files:
            self._current_files.remove(file_path)
            self._detect_project_root()
            return True
        return False

    def clear_files(self) -> None:
        """Clear all files."""
        self._current_files = []
        self._project_root = None

    def expand_directories(
        self,
        paths: list[str],
        *,
        follow_symlinks: bool = False,
        max_depth: int | None = None,
        max_files: int | None = None,
    ) -> list[str]:
        """
        Expand directories into individual files.

        Args:
            paths: List of file/directory paths
            follow_symlinks: Whether to follow symbolic links
            max_depth: Maximum directory depth (None for unlimited)
            max_files: Maximum files to return (None for unlimited)

        Returns:
            List of file paths
        """
        result_files = []
        seen_files = set()

        for path_str in paths:
            path_obj = Path(path_str)

            if path_obj.is_file():
                # Add file directly
                if path_str not in seen_files:
                    result_files.append(path_str)
                    seen_files.add(path_str)
            elif path_obj.is_dir():
                # Expand directory
                dir_files = self._walk_directory(
                    path_str,
                    follow_symlinks=follow_symlinks,
                    max_depth=max_depth,
                    seen_files=seen_files,
                )

                for file_path in dir_files:
                    if file_path not in seen_files:
                        result_files.append(file_path)
                        seen_files.add(file_path)

                        # Check max files limit
                        if max_files and len(result_files) >= max_files:
                            return result_files

        return result_files

    def get_text_files(self) -> list[str]:
        """
        Get only text files from the current collection.

        Returns:
            List of text file paths
        """
        return [f for f in self._current_files if is_text_file(f)]

    def get_files_by_extension(self, extensions: list[str]) -> list[str]:
        """
        Get files matching specific extensions.

        Args:
            extensions: List of extensions (e.g., ['.py', '.js'])

        Returns:
            List of matching file paths
        """
        extensions_lower = [ext.lower() for ext in extensions]
        return [f for f in self._current_files if Path(f).suffix.lower() in extensions_lower]

    def group_by_directory(self) -> dict[str, list[str]]:
        """
        Group files by their parent directory.

        Returns:
            Dictionary mapping directory paths to file lists
        """
        groups: dict[str, list[str]] = {}

        for file_path in self._current_files:
            directory = str(Path(file_path).parent)
            if directory not in groups:
                groups[directory] = []
            groups[directory].append(file_path)

        return groups

    def get_common_root(self) -> Path | None:
        """
        Get the common root directory of all files.

        Returns:
            Common root Path or None if no common root
        """
        if not self._current_files:
            return None

        if len(self._current_files) == 1:
            return Path(self._current_files[0]).parent

        try:
            common = os.path.commonpath(self._current_files)
            return Path(common)
        except ValueError:
            # No common path (e.g., different drives on Windows)
            return None

    def _detect_project_root(self) -> None:
        """Detect project root from current files."""
        if not self._current_files:
            self._project_root = None
            return

        # Try to detect from first file
        first_file = self._current_files[0]
        root_str = detect_project_root(first_file)

        self._project_root = Path(root_str) if root_str else None

    def _walk_directory(
        self,
        directory: str,
        *,
        follow_symlinks: bool = False,
        max_depth: int | None = None,
        seen_files: set[str] | None = None,
        current_depth: int = 0,
    ) -> list[str]:
        """
        Recursively walk a directory to collect files.

        Args:
            directory: Directory path to walk
            follow_symlinks: Whether to follow symbolic links
            max_depth: Maximum depth to traverse
            seen_files: Set of already seen files (for deduplication)
            current_depth: Current recursion depth

        Returns:
            List of file paths
        """
        if seen_files is None:
            seen_files = set()

        if max_depth is not None and current_depth >= max_depth:
            return []

        files = []

        try:
            for root, _dirs, filenames in os.walk(directory, followlinks=follow_symlinks):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    file_path = os.path.abspath(file_path)  # Normalize path

                    if file_path not in seen_files:
                        files.append(file_path)
                        seen_files.add(file_path)

                # Check depth for subdirectories
                if max_depth is not None:
                    current_dir_depth = root[len(directory) :].count(os.sep)
                    if current_dir_depth >= max_depth:
                        break

        except (OSError, PermissionError):
            # Skip directories we can't access
            pass

        return files


class FileStats:
    """Provides statistics about a collection of files."""

    @staticmethod
    def get_total_size(files: list[str]) -> int:
        """
        Get total size of all files in bytes.

        Args:
            files: List of file paths

        Returns:
            Total size in bytes
        """
        total = 0
        for file_path in files:
            try:
                total += Path(file_path).stat().st_size
            except (OSError, FileNotFoundError):
                pass
        return total

    @staticmethod
    def get_file_count_by_type(files: list[str]) -> dict[str, int]:
        """
        Count files by extension.

        Args:
            files: List of file paths

        Returns:
            Dictionary mapping extensions to counts
        """
        counts: dict[str, int] = {}

        for file_path in files:
            ext = Path(file_path).suffix.lower() or "(no extension)"
            counts[ext] = counts.get(ext, 0) + 1

        return counts

    @staticmethod
    def get_text_file_percentage(files: list[str]) -> float:
        """
        Calculate percentage of text files.

        Args:
            files: List of file paths

        Returns:
            Percentage (0-100) of files that are text files
        """
        if not files:
            return 0.0

        text_count = sum(1 for f in files if is_text_file(f))
        return (text_count / len(files)) * 100
