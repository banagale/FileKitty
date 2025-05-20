import os
from pathlib import Path

from .constants import TEXT_CHECK_CHUNK_SIZE


# --- Helper Function ---
def is_text_file(file_path: str) -> bool:
    """
    Attempts to determine if a file is likely a text file.
    Checks for null bytes in the initial chunk and attempts UTF-8 decoding.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(TEXT_CHECK_CHUNK_SIZE)
            if b"\x00" in chunk:
                return False  # Null byte suggests binary
            # Try decoding as UTF-8. If it fails, likely not standard text.
            try:
                chunk.decode("utf-8")
                return True
            except UnicodeDecodeError:
                # Could try other encodings, but for simplicity, assume non-text
                return False
    except (OSError, FileNotFoundError):
        # Cannot read or access, treat as non-text for safety
        return False
    except Exception:
        # Catch any other unexpected errors during check
        return False


def read_file_contents(file_path):
    """Reads file content, trying common encodings."""
    # Prioritize UTF-8, then try others common on different platforms
    encodings_to_try = ["utf-8", "latin-1", "windows-1252"]
    for encoding in encodings_to_try:
        try:
            with open(file_path, encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue  # Try next encoding
        except FileNotFoundError:
            raise  # Re-raise FileNotFoundError immediately
        except Exception as e:
            # Catch other potential read errors (permissions, etc.)
            raise OSError(f"Error reading file {file_path} with {encoding}: {e}") from e
    # If all encodings fail
    raise UnicodeDecodeError(f"Could not decode file {file_path} with tried encodings: {', '.join(encodings_to_try)}.")


def sanitize_path(file_path: str) -> str:
    """Attempts to shorten the file path using '~' for the home directory."""
    try:
        path = Path(file_path).resolve()
        home_dir = Path.home().resolve()

        # Use is_relative_to if available (Python 3.9+)
        if hasattr(path, "is_relative_to") and path.is_relative_to(home_dir):
            return str(Path("~") / path.relative_to(home_dir))
        # Fallback for older Python or different drive letters on Windows
        # Convert both to strings for reliable comparison across OS/versions
        str_path = str(path)
        str_home = str(home_dir)
        if str_path.startswith(str_home):
            # Ensure a path separator follows the home dir part before replacing
            if len(str_path) > len(str_home) and str_path[len(str_home)] in (os.sep, os.altsep):
                return "~" + str_path[len(str_home) :]
            elif len(str_path) == len(str_home):  # Exact match to home dir
                return "~"
        # If not relative to home, return the absolute path
        return str(path)
    except Exception as e:
        # In case of any error (e.g., resolving issues), return original path
        print(f"Warning: Could not sanitize path '{file_path}': {e}")
        return file_path


def detect_language(file_path: str) -> str:
    """Returns a language identifier string based on file extension for Markdown code blocks."""
    suffix = Path(file_path).suffix.lower()
    # Common language mappings (expand as needed)
    lang_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".hpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".cs": "csharp",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".xml": "xml",
        ".md": "markdown",
        ".sh": "bash",
        ".rb": "ruby",
        ".php": "php",
        ".go": "go",
        ".rs": "rust",
        ".swift": "swift",
        ".kt": "kotlin",
        ".sql": "sql",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".dockerfile": "dockerfile",
        ".tf": "terraform",
        ".log": "log",
        ".txt": "",  # Default to no language for .txt
    }
    return lang_map.get(suffix, "")  # Return mapped language or empty string
