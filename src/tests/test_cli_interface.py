"""Tests for CLI interface."""

import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from filekitty.cli_interface import (
    CLIError,
    SessionManager,
    create_response,
    get_python_symbols,
    handle_get_python_symbols,
    handle_load_session,
    handle_process_files,
    handle_save_session,
    handle_update_selection,
)
from filekitty.models import PromptSession, SelectionState


@pytest.fixture
def session_manager():
    """Create a session manager for testing."""
    return SessionManager()


@pytest.fixture
def sample_python_file(tmp_path):
    """Create a sample Python file for testing."""
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        """
class MyClass:
    def method(self):
        pass

def my_function():
    pass

def another_function():
    return 42
"""
    )
    return str(file_path)


@pytest.fixture
def sample_text_file(tmp_path):
    """Create a sample text file for testing."""
    file_path = tmp_path / "readme.md"
    file_path.write_text("# Test File\n\nThis is a test file.")
    return str(file_path)


class TestSessionManager:
    """Test SessionManager class."""

    def test_create_session(self, session_manager, sample_python_file):
        """Test creating a session."""
        session_id = str(uuid.uuid4())
        files = [sample_python_file]
        selection_state = {"mode": "All Files", "selected_file": None, "selected_items": []}
        settings = {"include_tree": False, "include_date_modified": True}

        session = session_manager.create_session(session_id, files, selection_state, settings)

        assert session.id == session_id
        assert len(session.files) == 1
        assert len(session.file_metadata) == 1
        assert session.file_metadata[0].language == "python"
        assert session.output_text is not None

    def test_create_session_nonexistent_file(self, session_manager):
        """Test creating a session with nonexistent file."""
        session_id = str(uuid.uuid4())
        files = ["/nonexistent/file.py"]
        selection_state = {}
        settings = {}

        with pytest.raises(CLIError) as excinfo:
            session_manager.create_session(session_id, files, selection_state, settings)

        assert excinfo.value.error_type == "FileNotFoundError"

    def test_get_session(self, session_manager, sample_python_file):
        """Test retrieving a session."""
        session_id = str(uuid.uuid4())
        session = session_manager.create_session(session_id, [sample_python_file], {}, {})

        retrieved = session_manager.get_session(session_id)
        assert retrieved.id == session_id

    def test_get_nonexistent_session(self, session_manager):
        """Test retrieving a nonexistent session."""
        with pytest.raises(CLIError) as excinfo:
            session_manager.get_session("nonexistent")

        assert excinfo.value.error_type == "SessionError"

    def test_update_selection(self, session_manager, sample_python_file):
        """Test updating selection state."""
        session_id = str(uuid.uuid4())
        session = session_manager.create_session(session_id, [sample_python_file], {}, {})

        # Update selection
        new_selection = {
            "mode": "Single File",
            "selected_file": sample_python_file,
            "selected_items": ["MyClass", "my_function"],
        }

        output = session_manager.update_selection(session_id, new_selection)

        assert output is not None
        assert "MyClass" in output or "my_function" in output
        assert session_manager.sessions[session_id].selection_state.mode == "Single File"


class TestGetPythonSymbols:
    """Test get_python_symbols function."""

    def test_get_symbols(self, sample_python_file):
        """Test extracting symbols from Python file."""
        result = get_python_symbols([sample_python_file])

        assert sample_python_file in result["symbols"]
        symbols = result["symbols"][sample_python_file]

        assert "MyClass" in symbols["classes"]
        assert "my_function" in symbols["functions"]
        assert "another_function" in symbols["functions"]
        assert len(result["errors"]) == 0

    def test_get_symbols_nonexistent_file(self):
        """Test getting symbols from nonexistent file."""
        result = get_python_symbols(["/nonexistent/file.py"])

        assert len(result["errors"]) == 1
        assert result["errors"][0]["file"] == "/nonexistent/file.py"

    def test_get_symbols_non_python_file(self, sample_text_file):
        """Test getting symbols from non-Python file."""
        result = get_python_symbols([sample_text_file])

        # Should skip non-Python files
        assert sample_text_file not in result["symbols"]


class TestResponseCreation:
    """Test response creation functions."""

    def test_create_success_response(self):
        """Test creating a success response."""
        response = create_response("test_action", "session-123", True, payload={"data": "test"})

        assert response["action"] == "test_action"
        assert response["session_id"] == "session-123"
        assert response["success"] is True
        assert response["payload"]["data"] == "test"
        assert "timestamp" in response

    def test_create_error_response(self):
        """Test creating an error response."""
        error = CLIError("TestError", "Test error message", {"detail": "value"})
        response = create_response("test_action", "session-123", False, error={"type": error.error_type, "message": error.message, "details": error.details})

        assert response["action"] == "test_action"
        assert response["session_id"] == "session-123"
        assert response["success"] is False
        assert response["error"]["type"] == "TestError"
        assert response["error"]["message"] == "Test error message"


class TestHandlers:
    """Test action handlers."""

    def test_handle_process_files(self, session_manager, sample_python_file):
        """Test process_files handler."""
        session_id = str(uuid.uuid4())
        payload = {
            "files": [sample_python_file],
            "selection_state": {"mode": "All Files"},
            "settings": {"include_tree": False},
        }

        response = handle_process_files(session_manager, session_id, payload)

        assert response["success"] is True
        assert "prompt_session" in response["payload"]
        assert response["payload"]["prompt_session"]["id"] == session_id

    def test_handle_get_python_symbols(self, session_manager, sample_python_file):
        """Test get_python_symbols handler."""
        session_id = str(uuid.uuid4())
        payload = {"files": [sample_python_file]}

        response = handle_get_python_symbols(session_manager, session_id, payload)

        assert response["success"] is True
        assert "symbols" in response["payload"]
        assert sample_python_file in response["payload"]["symbols"]

    def test_handle_update_selection(self, session_manager, sample_python_file):
        """Test update_selection handler."""
        session_id = str(uuid.uuid4())
        session_manager.create_session(session_id, [sample_python_file], {}, {})

        payload = {
            "selection_state": {
                "mode": "Single File",
                "selected_file": sample_python_file,
                "selected_items": ["MyClass"],
            }
        }

        response = handle_update_selection(session_manager, session_id, payload)

        assert response["success"] is True
        assert "output_text" in response["payload"]

    def test_handle_save_session(self, session_manager, sample_python_file, tmp_path):
        """Test save_session handler."""
        session_id = str(uuid.uuid4())
        session_manager.create_session(session_id, [sample_python_file], {}, {})

        save_path = tmp_path / "session.json"
        payload = {"file_path": str(save_path)}

        response = handle_save_session(session_manager, session_id, payload)

        assert response["success"] is True
        assert response["payload"]["saved_path"] == str(save_path)
        assert save_path.exists()

        # Verify saved content
        saved_data = json.loads(save_path.read_text())
        assert saved_data["id"] == session_id

    def test_handle_load_session(self, session_manager, sample_python_file, tmp_path):
        """Test load_session handler."""
        # First create and save a session
        session_id = str(uuid.uuid4())
        session = session_manager.create_session(session_id, [sample_python_file], {}, {})

        save_path = tmp_path / "session.json"
        session.save_to_file(str(save_path))

        # Now load it
        new_session_id = str(uuid.uuid4())
        payload = {"file_path": str(save_path)}

        response = handle_load_session(session_manager, new_session_id, payload)

        assert response["success"] is True
        assert "prompt_session" in response["payload"]
        assert response["payload"]["prompt_session"]["id"] == session_id


class TestFileMetadata:
    """Test file metadata generation."""

    def test_python_file_metadata(self, session_manager, sample_python_file):
        """Test metadata for Python files."""
        session_id = str(uuid.uuid4())
        session = session_manager.create_session(session_id, [sample_python_file], {}, {})

        metadata = session.file_metadata[0]
        assert metadata.path == sample_python_file
        assert metadata.is_text_file is True
        assert metadata.language == "python"
        assert metadata.last_modified is not None
        assert metadata.file_hash is not None
        assert metadata.size_bytes > 0

    def test_text_file_metadata(self, session_manager, sample_text_file):
        """Test metadata for text files."""
        session_id = str(uuid.uuid4())
        session = session_manager.create_session(session_id, [sample_text_file], {}, {})

        metadata = session.file_metadata[0]
        assert metadata.path == sample_text_file
        assert metadata.is_text_file is True
        assert metadata.language == "markdown"


class TestOutputGeneration:
    """Test output generation."""

    def test_all_files_mode(self, session_manager, sample_python_file, sample_text_file):
        """Test output generation in All Files mode."""
        session_id = str(uuid.uuid4())
        files = [sample_python_file, sample_text_file]
        session = session_manager.create_session(session_id, files, {"mode": "All Files"}, {})

        output = session.output_text
        assert output is not None
        assert "sample.py" in output
        assert "readme.md" in output

    def test_single_file_mode(self, session_manager, sample_python_file):
        """Test output generation in Single File mode."""
        session_id = str(uuid.uuid4())
        session = session_manager.create_session(
            session_id,
            [sample_python_file],
            {"mode": "Single File", "selected_file": sample_python_file, "selected_items": []},
            {},
        )

        output = session.output_text
        assert output is not None
        assert "sample.py" in output

    def test_filtered_python_output(self, session_manager, sample_python_file):
        """Test filtered output for Python files."""
        session_id = str(uuid.uuid4())
        session = session_manager.create_session(
            session_id,
            [sample_python_file],
            {"mode": "Single File", "selected_file": sample_python_file, "selected_items": ["MyClass"]},
            {},
        )

        output = session.output_text
        assert output is not None
        assert "MyClass" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
