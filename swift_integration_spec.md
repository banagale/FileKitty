# FileKitty Swift Integration Specification

## Overview
This document defines the data exchange format and API contract between the Swift UI layer and Python backend for FileKitty.

## Communication Method
- **Primary**: JSON over subprocess CLI
- **Alternative**: PythonKit integration (TBD)

## Data Models

### Core Request/Response Structure

```json
{
  "action": "string",
  "session_id": "string",
  "payload": {},
  "timestamp": "ISO8601"
}
```

### Actions

#### 1. Process Files (`process_files`)
**Request:**
```json
{
  "action": "process_files",
  "session_id": "uuid",
  "payload": {
    "files": ["path1", "path2"],
    "selection_state": {
      "mode": "All Files",
      "selected_file": null,
      "selected_items": []
    },
    "settings": {
      "include_tree": true,
      "tree_base_dir": "",
      "tree_ignore_regex": "",
      "include_date_modified": true,
      "auto_copy": false
    }
  }
}
```

**Response:**
```json
{
  "action": "process_files",
  "session_id": "uuid",
  "success": true,
  "payload": {
    "prompt_session": {
      "id": "uuid",
      "timestamp": "2025-07-05T12:00:00Z",
      "files": ["path1", "path2"],
      "file_metadata": [
        {
          "path": "path1",
          "display_path": "file1.py",
          "is_text_file": true,
          "language": "python",
          "last_modified": "2025-07-05T11:30:00Z",
          "file_hash": "abc123",
          "size_bytes": 1024
        }
      ],
      "selection_state": {
        "mode": "All Files",
        "selected_file": null,
        "selected_items": []
      },
      "project_root": "/path/to/project",
      "tree_snapshot": {
        "base_path": "/path/to/project",
        "base_path_display": "project/",
        "ignore_regex": "\\.git|\\.pyc",
        "rendered": "# Folder Tree\\n\\n```text\\nproject/\\n├── file1.py\\n└── file2.py\\n```"
      },
      "output_text": "# Combined markdown output...",
      "settings": {}
    }
  }
}
```

#### 2. Get Python Classes/Functions (`get_python_symbols`)
**Request:**
```json
{
  "action": "get_python_symbols",
  "session_id": "uuid",
  "payload": {
    "files": ["file1.py", "file2.py"]
  }
}
```

**Response:**
```json
{
  "action": "get_python_symbols",
  "session_id": "uuid",
  "success": true,
  "payload": {
    "symbols": {
      "file1.py": {
        "classes": ["MyClass", "AnotherClass"],
        "functions": ["my_function", "helper_func"]
      },
      "file2.py": {
        "classes": [],
        "functions": ["main", "process"]
      }
    },
    "errors": []
  }
}
```

#### 3. Update Selection (`update_selection`)
**Request:**
```json
{
  "action": "update_selection",
  "session_id": "uuid",
  "payload": {
    "selection_state": {
      "mode": "Single File",
      "selected_file": "file1.py",
      "selected_items": ["MyClass", "my_function"]
    }
  }
}
```

**Response:**
```json
{
  "action": "update_selection",
  "session_id": "uuid",
  "success": true,
  "payload": {
    "output_text": "# Updated markdown output with filtered content..."
  }
}
```

#### 4. Save Session (`save_session`)
**Request:**
```json
{
  "action": "save_session",
  "session_id": "uuid",
  "payload": {
    "file_path": "/path/to/session.json"
  }
}
```

**Response:**
```json
{
  "action": "save_session",
  "session_id": "uuid",
  "success": true,
  "payload": {
    "saved_path": "/path/to/session.json"
  }
}
```

#### 5. Load Session (`load_session`)
**Request:**
```json
{
  "action": "load_session",
  "session_id": "uuid",
  "payload": {
    "file_path": "/path/to/session.json"
  }
}
```

**Response:**
```json
{
  "action": "load_session",
  "session_id": "uuid",
  "success": true,
  "payload": {
    "prompt_session": {
      // Full PromptSession object
    }
  }
}
```

### Error Response Format
```json
{
  "action": "action_name",
  "session_id": "uuid",
  "success": false,
  "error": {
    "type": "ValidationError",
    "message": "Invalid file path provided",
    "details": {},
    "debug": "Traceback (most recent call last):\n  File...\nValueError: Invalid path"
  }
}
```

**Note**: The `debug` field is optional and only included when `--debug` flag is used.

## CLI Interface

### Command Structure
```bash
filekitty <action> [options]
```

### Global Options
- `--json`: Output responses as newline-delimited JSON (NDJSON) for streaming
- `--debug`: Include Python tracebacks in error responses for debugging

### Examples
```bash
# Process files with JSON output
filekitty process_files --files file1.py file2.py --session-id abc123 --json

# Get symbols
filekitty get_python_symbols --files file1.py --session-id abc123

# Update selection with debug output
filekitty update_selection --session-id abc123 --mode "Single File" --selected-file file1.py --debug

# Stream processing with NDJSON
filekitty process_files --files *.py --json | while read line; do
  echo "Received: $line"
done
```

## Data Validation

### Required Fields
- `action`: Must be valid action name
- `session_id`: Must be valid UUID
- `payload`: Must contain required fields for action

### File Path Validation
- All file paths must be absolute
- Files must exist and be readable
- Paths must be within allowed directories (security)

## Error Handling

### Error Types
- `ValidationError`: Invalid input data
- `FileNotFoundError`: Requested file doesn't exist
- `PermissionError`: Cannot read file
- `ProcessingError`: Error during file processing
- `SessionError`: Session management error

## Security Considerations

### File Access
- Only allow access to files within project boundaries
- Validate all file paths to prevent directory traversal
- Implement file size limits

### Command Injection
- Sanitize all command line arguments
- Use subprocess with shell=False
- Validate JSON input structure