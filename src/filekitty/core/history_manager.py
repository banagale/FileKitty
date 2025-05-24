import hashlib
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QSettings, QStandardPaths

from filekitty.constants import (
    HASH_ERROR_SENTINEL,
    HASH_MISSING_SENTINEL,
    HISTORY_DIR_NAME,
    SETTINGS_HISTORY_PATH_KEY,
    STALE_CHECK_INTERVAL_MS,
)


class HistoryManager:
    def __init__(self, main_window_ref):
        self.main_window_ref = main_window_ref  # Reference to FilePicker instance
        self.history_dir: str = ""
        self.history_base_path: str = ""  # User-defined base path (or "" if default)
        self.history: list[dict] = []  # List of state dictionaries
        self.history_index: int = -1  # Current position in history
        self._is_loading_state: bool = False  # Flag to prevent updates during state load

        self._initialize_history_directory()

    def _initialize_history_directory(self) -> None:
        """Reads settings and sets up the history directory path."""
        settings = QSettings("Bastet", "FileKitty")
        # Use self.history_base_path if it's already set (e.g., by change_history_directory)
        # Otherwise, fetch from settings.
        stored_base_path = self.history_base_path or settings.value(SETTINGS_HISTORY_PATH_KEY, "")
        base_path_to_use = ""

        if stored_base_path and os.path.isdir(stored_base_path):
            base_path_to_use = stored_base_path
            self.history_base_path = stored_base_path
            print(f"Using user-defined history base path: {base_path_to_use}")
        else:
            temp_loc = QStandardPaths.writableLocation(QStandardPaths.TempLocation)
            if not temp_loc:
                home_cache = Path.home() / ".cache"
                lib_cache = Path.home() / "Library" / "Caches"
                if sys.platform == "darwin" and lib_cache.parent.exists():
                    temp_loc = str(lib_cache)
                elif home_cache.parent.exists():
                    temp_loc = str(home_cache)
                else:
                    temp_loc = "."
            base_path_to_use = str(temp_loc)
            self.history_base_path = ""  # Indicate default is used
            print(f"Using default history base path: {base_path_to_use}")

        history_path = Path(base_path_to_use) / HISTORY_DIR_NAME
        try:
            history_path.mkdir(parents=True, exist_ok=True)
            self.history_dir = str(history_path)
            print(f"History directory set to: {self.history_dir}")
        except OSError as e:
            self.history_dir = ""  # Disable history
            if self.main_window_ref:  # Check if main_window_ref is set
                self.main_window_ref.show_message_box(
                    "critical", "History Error", f"Could not create history directory:\n{history_path}\n{e}"
                )
            else:
                print(f"CRITICAL: Could not create history directory without main_window_ref: {history_path}\n{e}")

    def get_history_dir(self) -> str:
        return self.history_dir

    def set_history_dir(self, path: str):
        self.history_dir = path

    def get_history_base_path(self) -> str:
        return self.history_base_path

    def set_history_base_path(self, path: str):
        self.history_base_path = path

    def is_loading_state(self) -> bool:
        return self._is_loading_state

    def set_loading_state(self, is_loading: bool):
        self._is_loading_state = is_loading

    def get_history(self) -> list[dict]:
        return self.history

    def set_history(self, history: list[dict]):
        self.history = history

    def get_history_index(self) -> int:
        return self.history_index

    def set_history_index(self, index: int):
        self.history_index = index

    def get_stale_check_interval(self) -> int:
        return STALE_CHECK_INTERVAL_MS

    def calculate_file_hash(self, file_path: str) -> str:
        try:
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                while chunk := f.read(4096):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            return HASH_MISSING_SENTINEL
        except PermissionError:
            print(f"Permission error hashing file {file_path}")
            return HASH_ERROR_SENTINEL
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            return HASH_ERROR_SENTINEL

    def create_new_state(self, current_files, selected_items, selection_mode, selected_file, is_text_file_func):
        if self._is_loading_state or not self.history_dir:
            return

        current_text_files = [f for f in current_files if is_text_file_func(f)]
        file_hashes = {f: self.calculate_file_hash(f) for f in current_text_files}

        state = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "files": current_files,
            "selected_items": selected_items,
            "selection_mode": selection_mode,
            "selected_file": selected_file,
            "file_hashes": file_hashes,
        }

        if self.history_index >= 0 and self.history_index < len(self.history):
            last_state = self.history[self.history_index]
            keys_to_compare = ["files", "selected_items", "selection_mode", "selected_file", "file_hashes"]
            is_duplicate = all(state.get(k) == last_state.get(k) for k in keys_to_compare)
            if is_duplicate:
                print("Skipping save, state identical to previous.")
                return

        state_file_name = f"state_{state['id']}.json"
        state_file_path = os.path.join(self.history_dir, state_file_name)

        try:
            with open(state_file_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            if self.history_index < len(self.history) - 1:
                states_to_remove = self.history[self.history_index + 1 :]
                self.history = self.history[: self.history_index + 1]
                for old_state in states_to_remove:
                    old_file_path = os.path.join(self.history_dir, f"state_{old_state['id']}.json")
                    try:
                        os.remove(old_file_path)
                    except OSError as e:
                        print(f"Error removing old state file {old_file_path}: {e}")

            self.history.append(state)
            self.history_index = len(self.history) - 1

            if self.main_window_ref:
                self.main_window_ref._update_history_ui()
                self.main_window_ref._update_stale_status_display({})
        except Exception as e:
            if self.main_window_ref:
                self.main_window_ref.show_message_box("critical", "History Error", f"Could not save history state: {e}")
            else:
                print(f"CRITICAL: Could not save history state without main_window_ref: {e}")

    def load_state(self, state_index: int) -> dict | None:
        if not (0 <= state_index < len(self.history)):
            print(f"Invalid state index requested: {state_index} (History size: {len(self.history)})")
            return None

        self._is_loading_state = True
        loaded_state_data = None
        try:
            state_to_load = self.history[state_index]
            state_file_name = f"state_{state_to_load['id']}.json"
            state_file_path = os.path.join(self.history_dir, state_file_name)

            print(f"Loading state {state_index + 1} from {state_file_path}")
            with open(state_file_path, encoding="utf-8") as f:
                loaded_state_data = json.load(f)

            self.history_index = state_index
        except FileNotFoundError:
            if self.main_window_ref:
                self.main_window_ref.show_message_box(
                    "warning", "History Error", f"History state file not found:\n{state_file_path}"
                )
            # Remove broken state and adjust index
            del self.history[state_index]
            self.history_index = min(self.history_index, len(self.history) - 1)
            if self.main_window_ref:
                self.main_window_ref._update_history_ui()  # Update UI after removal
        except json.JSONDecodeError:
            if self.main_window_ref:
                self.main_window_ref.show_message_box(
                    "warning", "History Error", f"Could not parse history state file:\n{state_file_path}"
                )
            del self.history[state_index]
            self.history_index = min(self.history_index, len(self.history) - 1)
            if self.main_window_ref:
                self.main_window_ref._update_history_ui()
        except Exception as e:
            if self.main_window_ref:
                self.main_window_ref.show_message_box("critical", "History Error", f"Error loading state: {e}")
        finally:
            self._is_loading_state = False

        return loaded_state_data

    def check_stale_status(self, state_data: dict, is_text_file_func) -> dict:
        if not state_data:
            return {}
        stale_files = {}
        stored_hashes = state_data.get("file_hashes", {})
        files_to_check = list(stored_hashes.keys())

        for file_path in files_to_check:
            if is_text_file_func(file_path):
                current_hash = self.calculate_file_hash(file_path)
                stored_hash = stored_hashes.get(file_path)  # Use .get for safety
                if stored_hash is None:  # Should not happen if state was saved correctly
                    print(f"Warning: No stored hash for {file_path} in state.")
                    continue

                if current_hash == HASH_MISSING_SENTINEL:
                    stale_files[file_path] = "missing"
                elif current_hash == HASH_ERROR_SENTINEL:
                    stale_files[file_path] = "error"
                elif current_hash != stored_hash:
                    stale_files[file_path] = "modified"
        return stale_files

    def cleanup_history_files(self, specific_dir: str | None = None):
        cleanup_dir = specific_dir or self.history_dir
        if not cleanup_dir or not os.path.isdir(cleanup_dir):
            if not specific_dir:
                print("History directory not set or invalid, skipping history file cleanup.")
            return

        print(f"Cleaning up history files in: {cleanup_dir}")
        cleaned_count = 0
        error_count = 0
        try:
            for filename in os.listdir(cleanup_dir):
                if filename.startswith("state_") and filename.endswith(".json"):
                    file_path = os.path.join(cleanup_dir, filename)
                    try:
                        os.remove(file_path)
                        cleaned_count += 1
                    except OSError as e:
                        print(f"Error removing history file {file_path}: {e}")
                        error_count += 1
            print(f"Removed {cleaned_count} history state files.")
            if error_count:
                print(f"Failed to remove {error_count} history files.")
            if not specific_dir and cleanup_dir.endswith(HISTORY_DIR_NAME):
                try:
                    if not os.listdir(cleanup_dir):
                        os.rmdir(cleanup_dir)
                        print(f"Removed empty history directory: {cleanup_dir}")
                except OSError as e:
                    print(f"Could not remove history directory {cleanup_dir}: {e}")
        except Exception as e:
            print(f"An error occurred during history cleanup in {cleanup_dir}: {e}")

    def change_history_directory(self, new_base_path: str):
        if not self.main_window_ref:
            print("Cannot change history directory without main_window_ref.")
            return

        self.main_window_ref.staleCheckTimer.stop()
        self.cleanup_history_files(specific_dir=self.history_dir)

        self.history = []
        self.history_index = -1

        # Update history_base_path which _initialize_history_directory will use
        self.history_base_path = new_base_path
        # _initialize_history_directory will read from QSettings if new_base_path is empty
        # or if new_base_path is not a valid directory.
        # It also handles setting self.history_dir
        self._initialize_history_directory()

        self.main_window_ref._update_history_ui()

        if self.history_dir:  # Check if a valid directory was set up
            self.main_window_ref.staleCheckTimer.start(self.get_stale_check_interval())
            self.main_window_ref.show_message_box(
                "information",
                "History Path Changed",
                f"History location updated and existing history cleared."
                f"\nNew history will be stored in:\n{self.history_dir}",
            )
        else:
            self.main_window_ref.show_message_box(
                "warning",
                "History Path Error",
                "History location could not be set. History feature disabled.",
            )

    def get_current_state_data(self) -> dict | None:
        if 0 <= self.history_index < len(self.history):
            return self.history[self.history_index]
        return None

    def get_history_info(self) -> tuple[int, int]:
        return self.history_index, len(self.history)
