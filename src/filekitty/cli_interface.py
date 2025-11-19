"""CLI Interface for FileKitty Swift Integration.

This module provides the JSON-based CLI interface for communication between
the Swift UI layer and Python backend.
"""

import argparse
import hashlib
import json
import sys
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from filekitty.core.project_tree import generate_tree
from filekitty.core.python_parser import extract_code_and_imports, parse_python_file
from filekitty.core.utils import display_path, is_text_file, read_file_contents
from filekitty.models import FileMetadata, PromptSession, SelectionState, TreeSnapshot


class CLIError(Exception):
    """Base exception for CLI errors."""

    def __init__(self, error_type: str, message: str, details: dict | None = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)


class SessionManager:
    """Manages FileKitty sessions for the CLI interface."""

    def __init__(self):
        self.sessions: dict[str, PromptSession] = {}

    def create_session(
        self,
        session_id: str,
        files: list[str],
        selection_state: dict[str, Any],
        settings: dict[str, Any],
    ) -> PromptSession:
        """Create a new session by processing files."""
        # Validate files exist
        validated_files = []
        for file_path in files:
            path = Path(file_path).resolve()
            if not path.exists():
                raise CLIError("FileNotFoundError", f"File not found: {file_path}")
            if not path.is_file():
                raise CLIError("ValidationError", f"Not a file: {file_path}")
            validated_files.append(str(path))

        # Determine project root (common ancestor)
        project_root = self._find_project_root(validated_files)

        # Build file metadata
        file_metadata = []
        for file_path in validated_files:
            path = Path(file_path)
            metadata = self._build_file_metadata(path, project_root)
            file_metadata.append(metadata)

        # Create selection state
        sel_state = SelectionState(
            mode=selection_state.get("mode", "All Files"),
            selected_file=selection_state.get("selected_file"),
            selected_items=selection_state.get("selected_items", []),
        )

        # Generate tree snapshot if requested
        tree_snapshot = None
        if settings.get("include_tree", False):
            tree_base = settings.get("tree_base_dir") or project_root
            tree_ignore = settings.get("tree_ignore_regex") or r"\.git|\.pyc|__pycache__|\.DS_Store"
            try:
                _, tree_data = generate_tree(tree_base, tree_ignore, project_root=Path(project_root))
                tree_snapshot = TreeSnapshot.from_dict(tree_data)
            except Exception as e:
                print(f"Warning: Could not generate tree: {e}", file=sys.stderr)

        # Generate output text
        output_text = self._generate_output(validated_files, sel_state, file_metadata, tree_snapshot, settings)

        # Create session
        session = PromptSession(
            id=session_id,
            timestamp=datetime.now(),
            files=validated_files,
            file_metadata=file_metadata,
            selection_state=sel_state,
            project_root=project_root,
            tree_snapshot=tree_snapshot,
            output_text=output_text,
            settings=settings,
        )

        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> PromptSession:
        """Get an existing session."""
        if session_id not in self.sessions:
            raise CLIError("SessionError", f"Session not found: {session_id}")
        return self.sessions[session_id]

    def update_selection(self, session_id: str, selection_state: dict[str, Any]) -> str:
        """Update selection state and regenerate output."""
        session = self.get_session(session_id)

        # Update selection state
        session.selection_state = SelectionState(
            mode=selection_state.get("mode", "All Files"),
            selected_file=selection_state.get("selected_file"),
            selected_items=selection_state.get("selected_items", []),
        )

        # Regenerate output
        output_text = self._generate_output(
            session.files, session.selection_state, session.file_metadata, session.tree_snapshot, session.settings
        )
        session.output_text = output_text

        return output_text

    def _find_project_root(self, files: list[str]) -> str:
        """Find common ancestor directory for files."""
        if not files:
            return str(Path.cwd())

        paths = [Path(f).resolve() for f in files]
        if len(paths) == 1:
            return str(paths[0].parent)

        # Find common ancestor
        common = paths[0].parent
        for path in paths[1:]:
            while not str(path).startswith(str(common)):
                common = common.parent
                if common == common.parent:  # Reached root
                    break

        return str(common)

    def _build_file_metadata(self, path: Path, project_root: str) -> FileMetadata:
        """Build metadata for a single file."""
        is_text = is_text_file(str(path))
        language = None
        if is_text:
            language = self._detect_language(path)

        file_hash = None
        try:
            content = path.read_bytes()
            file_hash = hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            pass

        last_modified = None
        try:
            last_modified = datetime.fromtimestamp(path.stat().st_mtime)
        except Exception:
            pass

        display = display_path(path, Path(project_root) if project_root else None)

        return FileMetadata(
            path=str(path),
            display_path=display,
            is_text_file=is_text,
            language=language,
            last_modified=last_modified,
            file_hash=file_hash,
            size_bytes=path.stat().st_size,
        )

    def _detect_language(self, path: Path) -> str | None:
        """Detect programming language from file extension."""
        ext = path.suffix.lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".rs": "rust",
            ".go": "go",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".cs": "csharp",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".md": "markdown",
            ".sh": "bash",
        }
        return language_map.get(ext)

    def _generate_output(
        self,
        files: list[str],
        selection_state: SelectionState,
        file_metadata: list[FileMetadata],
        tree_snapshot: TreeSnapshot | None,
        settings: dict[str, Any],
    ) -> str:
        """Generate markdown output based on current selection."""
        output_parts = []

        # Add tree if available
        if tree_snapshot:
            output_parts.append(tree_snapshot.rendered)
            output_parts.append("")

        # Add file contents
        if selection_state.mode == "All Files":
            # Show all files
            for file_path, metadata in zip(files, file_metadata):
                if metadata.is_text_file:
                    output_parts.append(self._format_file_content(file_path, metadata, settings))
                    output_parts.append("")
        elif selection_state.mode == "Single File" and selection_state.selected_file:
            # Show single file with optional filtering
            file_path = selection_state.selected_file
            metadata = next((m for m in file_metadata if m.path == file_path), None)

            if metadata:
                if selection_state.selected_items and metadata.language == "python":
                    # Extract specific symbols
                    output_parts.append(self._format_filtered_python(file_path, metadata, selection_state, settings))
                else:
                    # Show full file
                    output_parts.append(self._format_file_content(file_path, metadata, settings))
                output_parts.append("")

        return "\n".join(output_parts).strip()

    def _format_file_content(self, file_path: str, metadata: FileMetadata, settings: dict[str, Any]) -> str:
        """Format a complete file for output."""
        parts = [f"# File: {metadata.display_path}"]

        if settings.get("include_date_modified") and metadata.last_modified:
            parts.append(f"*Last modified: {metadata.last_modified.strftime('%Y-%m-%d %H:%M:%S')}*")

        parts.append("")
        parts.append(f"```{metadata.language or 'text'}")

        try:
            content = read_file_contents(file_path)
            parts.append(content.rstrip())
        except Exception as e:
            parts.append(f"Error reading file: {e}")

        parts.append("```")

        return "\n".join(parts)

    def _format_filtered_python(
        self, file_path: str, metadata: FileMetadata, selection_state: SelectionState, settings: dict[str, Any]
    ) -> str:
        """Format filtered Python code for output."""
        try:
            content = read_file_contents(file_path)
            modified_line = ""
            if settings.get("include_date_modified") and metadata.last_modified:
                modified_line = f"*Last modified: {metadata.last_modified.strftime('%Y-%m-%d %H:%M:%S')}*"

            return extract_code_and_imports(
                content, selection_state.selected_items, metadata.display_path, modified_line
            )
        except Exception as e:
            return f"# Error extracting code from {metadata.display_path}: {e}\n"


def get_python_symbols(files: list[str]) -> dict[str, Any]:
    """Extract classes and functions from Python files."""
    symbols = {}
    errors = []

    for file_path in files:
        path = Path(file_path).resolve()
        if not path.exists():
            errors.append({"file": file_path, "error": "File not found"})
            continue

        if path.suffix.lower() != ".py":
            continue

        try:
            classes, functions, _, _ = parse_python_file(str(path))
            symbols[file_path] = {"classes": classes, "functions": functions}
        except Exception as e:
            errors.append({"file": file_path, "error": str(e)})

    return {"symbols": symbols, "errors": errors}


def create_response(
    action: str, session_id: str, success: bool, payload: dict[str, Any] | None = None, error: dict | None = None
) -> dict[str, Any]:
    """Create a standardized response object."""
    response = {"action": action, "session_id": session_id, "success": success, "timestamp": datetime.now().isoformat()}

    if payload is not None:
        response["payload"] = payload

    if error is not None:
        response["error"] = error

    return response


def create_error_response(action: str, session_id: str, error: CLIError, debug: bool = False) -> dict[str, Any]:
    """Create an error response."""
    error_dict = {"type": error.error_type, "message": error.message, "details": error.details}

    if debug:
        error_dict["debug"] = traceback.format_exc()

    return create_response(action, session_id, False, error=error_dict)


def handle_process_files(
    session_manager: SessionManager, session_id: str, payload: dict[str, Any], debug: bool = False
) -> dict[str, Any]:
    """Handle process_files action."""
    try:
        files = payload.get("files", [])
        selection_state = payload.get("selection_state", {})
        settings = payload.get("settings", {})

        session = session_manager.create_session(session_id, files, selection_state, settings)

        return create_response(action="process_files", session_id=session_id, success=True, payload={"prompt_session": session.to_dict()})
    except CLIError as e:
        return create_error_response("process_files", session_id, e, debug)
    except Exception as e:
        error = CLIError("ProcessingError", str(e))
        return create_error_response("process_files", session_id, error, debug)


def handle_get_python_symbols(
    session_manager: SessionManager, session_id: str, payload: dict[str, Any], debug: bool = False
) -> dict[str, Any]:
    """Handle get_python_symbols action."""
    try:
        files = payload.get("files", [])
        result = get_python_symbols(files)

        return create_response(action="get_python_symbols", session_id=session_id, success=True, payload=result)
    except CLIError as e:
        return create_error_response("get_python_symbols", session_id, e, debug)
    except Exception as e:
        error = CLIError("ProcessingError", str(e))
        return create_error_response("get_python_symbols", session_id, error, debug)


def handle_update_selection(
    session_manager: SessionManager, session_id: str, payload: dict[str, Any], debug: bool = False
) -> dict[str, Any]:
    """Handle update_selection action."""
    try:
        selection_state = payload.get("selection_state", {})
        output_text = session_manager.update_selection(session_id, selection_state)

        return create_response(action="update_selection", session_id=session_id, success=True, payload={"output_text": output_text})
    except CLIError as e:
        return create_error_response("update_selection", session_id, e, debug)
    except Exception as e:
        error = CLIError("ProcessingError", str(e))
        return create_error_response("update_selection", session_id, error, debug)


def handle_save_session(
    session_manager: SessionManager, session_id: str, payload: dict[str, Any], debug: bool = False
) -> dict[str, Any]:
    """Handle save_session action."""
    try:
        file_path = payload.get("file_path")
        if not file_path:
            raise CLIError("ValidationError", "file_path is required")

        session = session_manager.get_session(session_id)
        session.save_to_file(file_path)

        return create_response(action="save_session", session_id=session_id, success=True, payload={"saved_path": file_path})
    except CLIError as e:
        return create_error_response("save_session", session_id, e, debug)
    except Exception as e:
        error = CLIError("ProcessingError", str(e))
        return create_error_response("save_session", session_id, error, debug)


def handle_load_session(
    session_manager: SessionManager, session_id: str, payload: dict[str, Any], debug: bool = False
) -> dict[str, Any]:
    """Handle load_session action."""
    try:
        file_path = payload.get("file_path")
        if not file_path:
            raise CLIError("ValidationError", "file_path is required")

        session = PromptSession.load_from_file(file_path)
        session_manager.sessions[session_id] = session

        return create_response(action="load_session", session_id=session_id, success=True, payload={"prompt_session": session.to_dict()})
    except CLIError as e:
        return create_error_response("load_session", session_id, e, debug)
    except Exception as e:
        error = CLIError("ProcessingError", str(e))
        return create_error_response("load_session", session_id, error, debug)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="FileKitty CLI Interface for Swift Integration")
    parser.add_argument("action", help="Action to perform")
    parser.add_argument("--session-id", default=None, help="Session ID (UUID)")
    parser.add_argument("--json-input", help="JSON input string")
    parser.add_argument("--debug", action="store_true", help="Include debug information in errors")

    args = parser.parse_args()

    # Generate session ID if not provided
    session_id = args.session_id or str(uuid.uuid4())

    # Parse JSON input from stdin if not provided as argument
    if args.json_input:
        request_data = json.loads(args.json_input)
    else:
        try:
            request_data = json.load(sys.stdin)
        except json.JSONDecodeError:
            error_response = create_response(
                args.action,
                session_id,
                False,
                error={"type": "ValidationError", "message": "Invalid JSON input"},
            )
            print(json.dumps(error_response))
            sys.exit(1)

    # Extract payload
    payload = request_data.get("payload", {})

    # Initialize session manager
    session_manager = SessionManager()

    # Route to appropriate handler
    handlers = {
        "process_files": handle_process_files,
        "get_python_symbols": handle_get_python_symbols,
        "update_selection": handle_update_selection,
        "save_session": handle_save_session,
        "load_session": handle_load_session,
    }

    handler = handlers.get(args.action)
    if not handler:
        error_response = create_response(
            args.action,
            session_id,
            False,
            error={"type": "ValidationError", "message": f"Unknown action: {args.action}"},
        )
        print(json.dumps(error_response))
        sys.exit(1)

    # Execute handler
    response = handler(session_manager, session_id, payload, args.debug)

    # Output response
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
