"""Data models for FileKitty Swift integration."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class FileMetadata:
    """Metadata for a single file in the session."""

    path: str
    display_path: str
    is_text_file: bool
    language: Optional[str] = None
    last_modified: Optional[datetime] = None
    file_hash: Optional[str] = None
    size_bytes: Optional[int] = None


@dataclass
class TreeSnapshot:
    """File tree snapshot data."""

    base_path: str
    base_path_display: str
    ignore_regex: str
    rendered: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_path": self.base_path,
            "base_path_display": self.base_path_display,
            "ignore_regex": self.ignore_regex,
            "rendered": self.rendered,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreeSnapshot":
        return cls(
            base_path=data["base_path"],
            base_path_display=data["base_path_display"],
            ignore_regex=data["ignore_regex"],
            rendered=data["rendered"],
        )


@dataclass
class SelectionState:
    """Current file and code selection state."""

    mode: str = "All Files"  # "All Files" or "Single File"
    selected_file: Optional[str] = None
    selected_items: List[str] = field(default_factory=list)  # Classes/functions


@dataclass
class PromptSession:
    """Complete session state for FileKitty."""

    id: str
    timestamp: datetime
    files: List[str]
    file_metadata: List[FileMetadata]
    selection_state: SelectionState
    project_root: Optional[str] = None
    tree_snapshot: Optional[TreeSnapshot] = None
    output_text: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "files": self.files,
            "file_metadata": [
                {
                    "path": fm.path,
                    "display_path": fm.display_path,
                    "is_text_file": fm.is_text_file,
                    "language": fm.language,
                    "last_modified": fm.last_modified.isoformat() if fm.last_modified else None,
                    "file_hash": fm.file_hash,
                    "size_bytes": fm.size_bytes,
                }
                for fm in self.file_metadata
            ],
            "selection_state": {
                "mode": self.selection_state.mode,
                "selected_file": self.selection_state.selected_file,
                "selected_items": self.selection_state.selected_items,
            },
            "project_root": self.project_root,
            "tree_snapshot": self.tree_snapshot.to_dict() if self.tree_snapshot else None,
            "output_text": self.output_text,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptSession":
        """Create from dictionary (JSON deserialization)."""
        file_metadata = []
        for fm_data in data.get("file_metadata", []):
            last_modified = None
            if fm_data.get("last_modified"):
                last_modified = datetime.fromisoformat(fm_data["last_modified"])

            file_metadata.append(
                FileMetadata(
                    path=fm_data["path"],
                    display_path=fm_data["display_path"],
                    is_text_file=fm_data["is_text_file"],
                    language=fm_data.get("language"),
                    last_modified=last_modified,
                    file_hash=fm_data.get("file_hash"),
                    size_bytes=fm_data.get("size_bytes"),
                )
            )

        selection_data = data.get("selection_state", {})
        selection_state = SelectionState(
            mode=selection_data.get("mode", "All Files"),
            selected_file=selection_data.get("selected_file"),
            selected_items=selection_data.get("selected_items", []),
        )

        tree_snapshot = None
        if data.get("tree_snapshot"):
            tree_snapshot = TreeSnapshot.from_dict(data["tree_snapshot"])

        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            files=data["files"],
            file_metadata=file_metadata,
            selection_state=selection_state,
            project_root=data.get("project_root"),
            tree_snapshot=tree_snapshot,
            output_text=data.get("output_text"),
            settings=data.get("settings", {}),
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "PromptSession":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def save_to_file(self, file_path: str) -> None:
        """Save session to JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load_from_file(cls, file_path: str) -> "PromptSession":
        """Load session from JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())
