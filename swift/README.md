# FileKitty Swift Application

A modern macOS application for FileKitty with a native SwiftUI interface communicating with the Python backend.

## Architecture

The application consists of two main components:

### 1. Python CLI Backend (`filekitty-cli`)
- JSON-based API for processing files
- Five main actions:
  - `process_files`: Process and analyze files
  - `get_python_symbols`: Extract Python classes/functions
  - `update_selection`: Update file/symbol selection
  - `save_session`: Save session to file
  - `load_session`: Load session from file

### 2. SwiftUI macOS Application
- Native drag-and-drop interface
- Sidebar navigation for session history
- Split-view layout (file list + output preview)
- Syntax-highlighted markdown preview
- Command Palette (⌘K) for quick actions
- Multiple workspace support

## Features

### Core Features
- **Drag-and-Drop**: Visual feedback when dropping files
- **Session Management**: Save/load/share sessions
- **Python Symbol Extraction**: Automatic detection of classes/functions
- **Live Preview**: Real-time syntax-highlighted output
- **File Tree**: Optional project structure visualization

### Advanced Features
- **Real-time Collaboration**: Share sessions via MultipeerConnectivity
- **Shortcuts Integration**: Automate workflows with Shortcuts.app
- **Quick Look Plugin**: Preview `.filekitty` files in Finder
- **Menu Bar Mode**: Quick access from the menu bar
- **iCloud Sync**: Sync sessions and preferences across devices

## Building the Project

### Requirements
- macOS 13.0 or later
- Xcode 15.0 or later
- Python 3.12+
- FileKitty Python package installed

### Setup

1. Install Python dependencies:
```bash
cd /home/user/FileKitty
poetry install
```

2. Open Xcode project:
```bash
cd swift/FileKittyApp
open FileKittyApp.xcodeproj
```

3. Build and run (⌘R)

## Project Structure

```
FileKittyApp/
├── FileKittyApp/                  # Main app target
│   ├── FileKittyApp.swift        # App entry point
│   ├── Models.swift               # Data models
│   ├── CLIInterface.swift         # Python CLI communication
│   ├── ContentView.swift          # Main UI
│   ├── FileKittyViewModel.swift   # View model
│   ├── SyntaxHighlightedTextView.swift
│   ├── CommandPaletteView.swift
│   ├── SettingsView.swift
│   ├── CloudSyncManager.swift     # iCloud sync
│   ├── CollaborationManager.swift # Real-time sharing
│   ├── ShortcutsProvider.swift    # Shortcuts integration
│   ├── MenuBarManager.swift       # Menu bar mode
│   └── Info.plist
└── FileKittyQuickLook/            # Quick Look extension
    ├── PreviewProvider.swift
    └── Info.plist
```

## Usage

### Basic Workflow

1. **Add Files**: Drag files onto the window or click + to select
2. **Select Symbols**: Expand Python files to choose classes/functions
3. **Preview Output**: View syntax-highlighted markdown in right pane
4. **Copy/Export**: Copy to clipboard or save session for later

### Command Palette (⌘K)

Press ⌘K to open the command palette:
- Open Files
- New Session
- Load Session
- Copy to Clipboard
- Export Session
- Share Session
- Refresh Output
- Clear Selection

### Keyboard Shortcuts

- ⌘N - New Session
- ⌘O - Open Files
- ⌘⇧O - Load Session
- ⌘K - Command Palette
- ⌘⇧S - Export Session
- ⌘⇧C - Copy Output

### Collaboration

1. Start sharing: Settings → Enable Collaboration
2. Nearby devices will auto-discover
3. Selection changes sync in real-time
4. Disconnect: Settings → Disable Collaboration

### Shortcuts Integration

FileKitty provides App Shortcuts for automation:

- **Process Files**: Process files and return markdown output
- **Get Python Symbols**: Extract classes/functions from Python files
- **Load Session**: Load and return session output

Create workflows in Shortcuts.app using these actions.

### iCloud Sync

Enable in Settings to:
- Sync sessions across all your Macs
- Backup session history automatically
- Share sessions via iCloud sharing

### Menu Bar Mode

Click the cat icon in the menu bar for:
- Quick file processing
- Recent sessions access
- One-click session loading

## API Reference

### Python CLI Interface

All API calls use JSON over stdin/stdout:

**Request Format:**
```json
{
  "action": "process_files",
  "session_id": "uuid",
  "payload": {},
  "timestamp": "2025-07-05T12:00:00Z"
}
```

**Response Format:**
```json
{
  "action": "process_files",
  "session_id": "uuid",
  "success": true,
  "payload": {},
  "timestamp": "2025-07-05T12:00:01Z"
}
```

**Error Format:**
```json
{
  "action": "process_files",
  "session_id": "uuid",
  "success": false,
  "error": {
    "type": "ValidationError",
    "message": "Invalid file path",
    "details": {}
  }
}
```

### Swift API

```swift
let cliInterface = CLIInterface()

// Process files
let session = try await cliInterface.processFiles(
    files: fileURLs,
    settings: settings
)

// Get Python symbols
let symbols = try await cliInterface.getPythonSymbols(files: fileURLs)

// Update selection
let output = try await cliInterface.updateSelection(
    sessionId: session.id,
    selectionState: selectionState
)

// Save/load sessions
try await cliInterface.saveSession(sessionId: session.id, toFile: fileURL)
let session = try await cliInterface.loadSession(fromFile: fileURL)
```

## Development

### Adding New Actions

1. **Python Backend** (`cli_interface.py`):
   - Add handler function: `handle_<action_name>`
   - Register in `handlers` dictionary
   - Update spec documentation

2. **Swift Frontend**:
   - Add method to `CLIInterface.swift`
   - Update models if needed
   - Add UI in appropriate view

### Testing

Run Python CLI tests:
```bash
poetry run pytest src/tests/
```

Build and test Swift app in Xcode (⌘U)

## Troubleshooting

### Python CLI Not Found
- Ensure `filekitty-cli` is installed: `poetry install`
- Check Python path in Settings
- Set `PYTHON_PATH` environment variable

### iCloud Not Working
- Check iCloud account in System Settings
- Enable iCloud Drive for FileKitty
- Check entitlements are configured

### Collaboration Not Connecting
- Ensure devices are on same network
- Check firewall settings
- Enable "Local Network" permission in System Settings

## License

MIT License - Copyright © 2025 Bastet

## Credits

- Python backend: FileKitty core library
- SwiftUI: Modern macOS interface
- CloudKit: iCloud synchronization
- MultipeerConnectivity: Real-time collaboration
- AppIntents: Shortcuts integration
- QuickLook: File preview extension
