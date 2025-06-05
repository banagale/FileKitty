import logging
import os
from collections.abc import Iterable
from pathlib import Path

from filekitty.constants import TEXT_CHECK_CHUNK_SIZE

logger = logging.getLogger(__name__)


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


DEFAULT_PROJECT_MARKERS = {
    "pyproject.toml",
    "setup.py",
    "requirements.txt",
    "package.json",
    "node_modules",
    "Cargo.toml",
    ".git",
    "pom.xml",
    "build.gradle",
}


def detect_project_root(files: Iterable[str], project_markers: set[str] = DEFAULT_PROJECT_MARKERS) -> Path | None:
    """Find likely project root by looking for marker files up from common ancestor of given file paths."""
    paths = [Path(f).resolve() for f in files]
    if not paths:
        return None

    try:
        common = Path(os.path.commonpath(paths))
    except ValueError:
        return None  # e.g., files on different drives

    for parent in [common] + list(common.parents):
        if any((parent / marker).exists() for marker in project_markers):
            return parent
        if parent == Path.home() or parent.parent == parent:
            break

    return common


def display_path(
    path: str | Path,
    project_root: Path | None = None,
    *,
    show_ellipsis: bool = False,
) -> str:
    """
    Format a path for display:
    - Always try to show as relative to HOME
    - If project_root is inside home, ellipsize between ~ and root if needed
    - Always show full path from root → file, including parent folders
    - Else fallback to absolute path
    """
    try:
        p = Path(path).expanduser().resolve()
        home = Path.home().resolve()

        if project_root:
            project_root = project_root.expanduser().resolve()

        # Ensure ~ prefix if possible
        if p.is_relative_to(home):
            rel_to_home = p.relative_to(home)
            parts = rel_to_home.parts

            # If project root is inside home and p is under project root
            if project_root and p.is_relative_to(project_root) and project_root.is_relative_to(home):
                rel_root_parts = project_root.relative_to(home).parts
                file_rel_parts = p.relative_to(project_root).parts

                if show_ellipsis and len(rel_root_parts) > 2:
                    abbreviated_root = f"{rel_root_parts[0]}/…/{rel_root_parts[-1]}"
                else:
                    abbreviated_root = "/".join(rel_root_parts)

                full_path = f"~/{abbreviated_root}/" + "/".join(file_rel_parts)
                return full_path

            # p is in home but not under project_root (or root is outside home)
            if show_ellipsis and len(parts) > 5:
                abbreviated = f"{parts[0]}/{parts[1]}/…/{parts[-2]}/{parts[-1]}"
                return f"~/{abbreviated}"
            return f"~/{rel_to_home}"

        # Else: not under home dir → show full absolute path
        return str(p)

    except Exception:
        logger.warning("display_path failed for %s", path)
        return str(path)
