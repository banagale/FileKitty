"""
Settings management service for FileKitty.

This service encapsulates all settings operations, providing a clean interface
and separating settings logic from UI code.

Refactored to replace direct QSettings access throughout the application.
"""

from dataclasses import dataclass
from pathlib import Path

from PyQt5.QtCore import QSettings

from filekitty.constants import (
    FILE_IGNORE_DEFAULT,
    SETTINGS_DEFAULT_PATH_KEY,
    SETTINGS_FILE_IGNORE_KEY,
    SETTINGS_HISTORY_PATH_KEY,
    SETTINGS_TREE_BASE_KEY,
    SETTINGS_TREE_DEF_BASE_KEY,
    SETTINGS_TREE_DEF_IGNORE_KEY,
    SETTINGS_TREE_ENABLED_KEY,
    SETTINGS_TREE_IGNORE_KEY,
    TREE_IGNORE_DEFAULT,
)


@dataclass
class TreeSettings:
    """Settings related to project tree visualization."""

    enabled: bool = True
    base_directory: str = ""
    ignore_pattern: str = TREE_IGNORE_DEFAULT
    default_base: str = ""
    default_ignore: str = TREE_IGNORE_DEFAULT


@dataclass
class ApplicationSettings:
    """Complete application settings."""

    default_path: str = ""
    history_path: str = ""
    file_ignore_pattern: str = FILE_IGNORE_DEFAULT
    tree: TreeSettings = None

    def __post_init__(self):
        if self.tree is None:
            self.tree = TreeSettings()


class SettingsManager:
    """
    Manages application settings with a clean interface.

    This class provides a facade over QSettings and ensures type-safe access
    to configuration values.
    """

    def __init__(self, organization: str = "Bastet", application: str = "FileKitty"):
        """
        Initialize the settings manager.

        Args:
            organization: Organization name for QSettings
            application: Application name for QSettings
        """
        self._settings = QSettings(organization, application)

    def load_settings(self) -> ApplicationSettings:
        """
        Load all application settings.

        Returns:
            ApplicationSettings instance with current values
        """
        tree_settings = TreeSettings(
            enabled=self._get_bool(SETTINGS_TREE_ENABLED_KEY, True),
            base_directory=self._get_str(SETTINGS_TREE_BASE_KEY, ""),
            ignore_pattern=self._get_str(SETTINGS_TREE_IGNORE_KEY, ""),
            default_base=self._get_str(SETTINGS_TREE_DEF_BASE_KEY, ""),
            default_ignore=self._get_str(SETTINGS_TREE_DEF_IGNORE_KEY, TREE_IGNORE_DEFAULT),
        )

        # Apply defaults if not set
        if not tree_settings.ignore_pattern:
            tree_settings.ignore_pattern = tree_settings.default_ignore

        return ApplicationSettings(
            default_path=self._get_str(SETTINGS_DEFAULT_PATH_KEY, ""),
            history_path=self._get_str(SETTINGS_HISTORY_PATH_KEY, ""),
            file_ignore_pattern=self._get_str(SETTINGS_FILE_IGNORE_KEY, FILE_IGNORE_DEFAULT),
            tree=tree_settings,
        )

    def save_settings(self, settings: ApplicationSettings) -> None:
        """
        Save application settings.

        Args:
            settings: ApplicationSettings instance to save
        """
        self._set_str(SETTINGS_DEFAULT_PATH_KEY, settings.default_path)
        self._set_str(SETTINGS_HISTORY_PATH_KEY, settings.history_path)
        self._set_str(SETTINGS_FILE_IGNORE_KEY, settings.file_ignore_pattern)

        if settings.tree:
            self._set_bool(SETTINGS_TREE_ENABLED_KEY, settings.tree.enabled)
            self._set_str(SETTINGS_TREE_BASE_KEY, settings.tree.base_directory)
            self._set_str(SETTINGS_TREE_IGNORE_KEY, settings.tree.ignore_pattern)
            self._set_str(SETTINGS_TREE_DEF_BASE_KEY, settings.tree.default_base)
            self._set_str(SETTINGS_TREE_DEF_IGNORE_KEY, settings.tree.default_ignore)

        self._settings.sync()

    def get_default_path(self) -> str:
        """Get the default file selection path."""
        return self._get_str(SETTINGS_DEFAULT_PATH_KEY, str(Path.home()))

    def set_default_path(self, path: str) -> None:
        """Set the default file selection path."""
        self._set_str(SETTINGS_DEFAULT_PATH_KEY, path)

    def get_history_path(self) -> str:
        """Get the history storage path."""
        return self._get_str(SETTINGS_HISTORY_PATH_KEY, "")

    def set_history_path(self, path: str) -> None:
        """Set the history storage path."""
        self._set_str(SETTINGS_HISTORY_PATH_KEY, path)

    def get_file_ignore_pattern(self) -> str:
        """Get the file ignore regex pattern."""
        return self._get_str(SETTINGS_FILE_IGNORE_KEY, FILE_IGNORE_DEFAULT)

    def set_file_ignore_pattern(self, pattern: str) -> None:
        """Set the file ignore regex pattern."""
        self._set_str(SETTINGS_FILE_IGNORE_KEY, pattern)

    def is_tree_enabled(self) -> bool:
        """Check if tree visualization is enabled."""
        return self._get_bool(SETTINGS_TREE_ENABLED_KEY, True)

    def set_tree_enabled(self, enabled: bool) -> None:
        """Enable or disable tree visualization."""
        self._set_bool(SETTINGS_TREE_ENABLED_KEY, enabled)

    def get_tree_settings(self) -> TreeSettings:
        """Get all tree-related settings."""
        settings = self.load_settings()
        return settings.tree

    def update_tree_settings(self, tree_settings: TreeSettings) -> None:
        """Update tree-related settings."""
        self._set_bool(SETTINGS_TREE_ENABLED_KEY, tree_settings.enabled)
        self._set_str(SETTINGS_TREE_BASE_KEY, tree_settings.base_directory)
        self._set_str(SETTINGS_TREE_IGNORE_KEY, tree_settings.ignore_pattern)
        self._set_str(SETTINGS_TREE_DEF_BASE_KEY, tree_settings.default_base)
        self._set_str(SETTINGS_TREE_DEF_IGNORE_KEY, tree_settings.default_ignore)
        self._settings.sync()

    def clear_all(self) -> None:
        """Clear all application settings."""
        self._settings.clear()
        self._settings.sync()

    # Private helper methods

    def _get_str(self, key: str, default: str = "") -> str:
        """Get a string value from settings."""
        value = self._settings.value(key, default)
        return str(value) if value is not None else default

    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean value from settings."""
        value = self._settings.value(key, "true" if default else "false")
        return str(value).lower() == "true"

    def _get_int(self, key: str, default: int = 0) -> int:
        """Get an integer value from settings."""
        try:
            return int(self._settings.value(key, default))
        except (TypeError, ValueError):
            return default

    def _set_str(self, key: str, value: str) -> None:
        """Set a string value in settings."""
        self._settings.setValue(key, value)

    def _set_bool(self, key: str, value: bool) -> None:
        """Set a boolean value in settings."""
        self._settings.setValue(key, "true" if value else "false")

    def _set_int(self, key: str, value: int) -> None:
        """Set an integer value in settings."""
        self._settings.setValue(key, value)


class SettingsValidator:
    """Validates settings values before saving."""

    @staticmethod
    def validate_path(path: str) -> tuple[bool, str]:
        """
        Validate a file system path.

        Args:
            path: Path string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not path:
            return True, ""  # Empty is valid

        try:
            path_obj = Path(path)
            if path_obj.exists() and not path_obj.is_dir():
                return False, "Path must be a directory"
            return True, ""
        except (OSError, ValueError) as e:
            return False, f"Invalid path: {e}"

    @staticmethod
    def validate_regex(pattern: str) -> tuple[bool, str]:
        """
        Validate a regex pattern.

        Args:
            pattern: Regex pattern to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not pattern:
            return True, ""  # Empty is valid

        import re

        try:
            re.compile(pattern)
            return True, ""
        except re.error as e:
            return False, f"Invalid regex: {e}"
