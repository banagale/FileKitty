"""Unit tests for FileKitty data models - ensures JSON schema stability."""
# ruff: noqa: UP017

import json
import uuid
from datetime import datetime, timezone

from src.filekitty.models import FileMetadata, PromptSession, SelectionState, TreeSnapshot


def test_prompt_session_json_round_trip():
    """Test PromptSession to_json → from_json round-trip maintains data integrity."""
    # Create test data with UTC timestamps
    session = PromptSession(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        files=["/path/to/file1.py", "/path/to/file2.js"],
        file_metadata=[
            FileMetadata(
                path="/path/to/file1.py",
                display_path="file1.py",
                is_text_file=True,
                language="python",
                last_modified=datetime.now(timezone.utc),
                file_hash="abc123",
                size_bytes=1024,
            ),
            FileMetadata(
                path="/path/to/file2.js",
                display_path="file2.js",
                is_text_file=True,
                language="javascript",
                last_modified=datetime.now(timezone.utc),
                file_hash="def456",
                size_bytes=512,
            ),
        ],
        selection_state=SelectionState(
            mode="Single File", selected_file="/path/to/file1.py", selected_items=["MyClass", "my_function"]
        ),
        project_root="/path/to",
        tree_snapshot=TreeSnapshot(
            base_path="/path/to",
            base_path_display="project/",
            ignore_regex=r"\.git|\.pyc",
            rendered="# Tree\n```\nproject/\n├── file1.py\n└── file2.js\n```",
        ),
        output_text="# Generated output...",
        settings={"include_tree": True, "auto_copy": False},
    )

    # Convert to JSON and back
    json_str = session.to_json()
    parsed_session = PromptSession.from_json(json_str)

    # Verify round-trip integrity
    assert parsed_session.id == session.id
    assert parsed_session.timestamp == session.timestamp
    assert parsed_session.files == session.files
    assert len(parsed_session.file_metadata) == len(session.file_metadata)
    assert parsed_session.file_metadata[0].path == session.file_metadata[0].path
    assert parsed_session.file_metadata[0].language == session.file_metadata[0].language
    assert parsed_session.selection_state.mode == session.selection_state.mode
    assert parsed_session.selection_state.selected_items == session.selection_state.selected_items
    assert parsed_session.project_root == session.project_root
    assert parsed_session.tree_snapshot.base_path == session.tree_snapshot.base_path
    assert parsed_session.output_text == session.output_text
    assert parsed_session.settings == session.settings

    # Verify JSON contains expected UTC timestamp format
    parsed_json = json.loads(json_str)
    assert parsed_json["timestamp"].endswith("Z") or "+" in parsed_json["timestamp"]

    print("✅ PromptSession JSON round-trip test passed")


def test_timestamp_utc_format():
    """Test that timestamps are properly formatted with UTC timezone."""
    session = PromptSession(
        id="test-id", timestamp=datetime.now(timezone.utc), files=[], file_metadata=[], selection_state=SelectionState()
    )

    json_data = session.to_dict()
    timestamp_str = json_data["timestamp"]

    # Should end with Z (UTC) or have timezone offset
    assert timestamp_str.endswith("Z") or ("+" in timestamp_str) or ("-" in timestamp_str)

    # Should be parseable by Swift ISO8601DateFormatter
    parsed_back = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    assert parsed_back.tzinfo is not None

    print(f"✅ UTC timestamp format test passed: {timestamp_str}")


if __name__ == "__main__":
    test_prompt_session_json_round_trip()
    test_timestamp_utc_format()
    print("🎉 All model tests passed - JSON schema is stable!")
