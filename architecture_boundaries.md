# FileKitty Architecture Boundaries: Python vs Swift

## Overview
This document defines the clear separation of responsibilities between Python backend and Swift UI for FileKitty's hybrid architecture.

## Python Backend Responsibilities

### Core Logic (✅ Stays in Python)
- **File Processing**: Reading, parsing, and content extraction
- **Tree Generation**: Directory traversal and markdown tree creation
- **Python Code Analysis**: AST parsing for classes/functions
- **Content Aggregation**: Combining files into markdown output
- **Hash Calculation**: File integrity and staleness detection
- **Language Detection**: File type and syntax highlighting determination
- **Project Root Detection**: Finding repository/project boundaries

### Data Management (✅ Stays in Python)
- **Session Serialization**: JSON conversion and file I/O
- **History Management**: State persistence and navigation
- **Settings Storage**: Configuration and preferences
- **File Metadata**: Size, modification dates, permissions
- **Error Handling**: File access and processing errors

### Business Logic (✅ Stays in Python)
- **Output Filtering**: Ignore patterns and file exclusion
- **Content Formatting**: Markdown generation and styling
- **Selection Logic**: Class/function filtering
- **Path Normalization**: Display paths and project-relative paths
- **Validation**: Input sanitization and security checks

## Swift UI Responsibilities

### User Interface (🔄 Migrates to Swift)
- **File List Display**: Tree view of selected files
- **File Selection**: Drag & drop, file picker dialogs
- **Text Display**: Markdown rendering and syntax highlighting
- **Navigation**: History back/forward buttons
- **Settings UI**: Preferences and configuration panels
- **Progress Indicators**: Loading states and operation feedback

### User Interactions (🔄 Migrates to Swift)
- **Drag & Drop**: File and folder handling
- **Context Menus**: Right-click actions
- **Keyboard Shortcuts**: Navigation and actions
- **Copy/Paste**: Clipboard operations
- **Export/Save**: File output operations
- **Search/Filter**: UI-level filtering and navigation

### Platform Integration (🔄 Migrates to Swift)
- **macOS Integration**: Dock, menu bar, notifications
- **File System Access**: Sandboxed file operations
- **Window Management**: Sizing, positioning, multi-window
- **Accessibility**: VoiceOver and assistive technologies
- **Dark Mode**: Theme and appearance handling

## Shared/Bridge Layer

### Data Exchange (🔄 New Implementation)
- **JSON Communication**: Request/response handling
- **Session Management**: State synchronization
- **Error Propagation**: Python errors to Swift UI
- **Progress Updates**: Long-running operation status
- **Validation**: Input/output data verification

### CLI Interface (🔄 New Implementation)
- **Command Processing**: Python CLI entry point
- **Argument Parsing**: Swift → Python parameter passing
- **Output Formatting**: Structured JSON responses
- **Error Handling**: Consistent error format
- **Process Management**: Python subprocess lifecycle

## Migration Strategy

### Phase 1: Foundation
1. **Keep Python Logic Intact**: No changes to core processing
2. **Create CLI Interface**: New command-line entry point
3. **Implement Data Models**: PromptSession and supporting classes
4. **Define JSON Schema**: Request/response contracts

### Phase 2: Bridge Implementation
1. **Python CLI Module**: Handle Swift → Python communication
2. **Swift HTTP/Process Client**: Handle Python subprocess calls
3. **Data Serialization**: JSON encoding/decoding on both sides
4. **Error Handling**: Consistent error propagation

### Phase 3: UI Migration
1. **File List View**: Replace PyQt5 QListWidget
2. **Text Display**: Replace PyQt5 QTextEdit
3. **Menu/Toolbar**: Replace PyQt5 menus
4. **Settings Dialog**: Replace PyQt5 preferences

### Phase 4: Polish
1. **Platform Features**: macOS-specific integration
2. **Performance**: Optimize Swift ↔ Python communication
3. **Testing**: Comprehensive integration testing
4. **Documentation**: User guides and API docs

### Phase 5: Packaging & Release
1. **Swift Build**: `swift build -c release` for optimized binary
2. **Code Signing**: Sign SwiftUI app with developer certificate
3. **DMG Creation**: `create-dmg` with custom background and layout
4. **Notarization**: Submit to Apple for security approval
5. **GitHub Release**: `gh release create v0-swift-alpha` with signed DMG
6. **Release Notes**: Document new SwiftUI features and migration notes

## Key Principles

### 1. Minimal Python Changes
- Keep existing Python logic unchanged where possible
- Add new CLI interface without breaking existing code
- Maintain backward compatibility with current features

### 2. Clear Separation
- Python: Data processing, business logic, file operations
- Swift: UI, user interaction, platform integration
- Bridge: Communication, serialization, error handling

### 3. Incremental Migration
- Start with basic file processing
- Add features incrementally
- Maintain working application at each step

### 4. Data Integrity
- Consistent data models between Python and Swift
- Comprehensive validation and error handling
- Atomic operations where possible

## Benefits of This Architecture

### For Python
- **Leverage Existing Code**: Minimal rewrite required
- **Maintain Complexity**: Keep sophisticated logic in Python
- **Cross-Platform**: Python backend remains portable
- **Testing**: Existing Python tests continue to work

### For Swift
- **Native Performance**: Fast, responsive UI
- **Platform Integration**: Full macOS feature support
- **Modern UX**: SwiftUI declarative interface
- **Maintainability**: Type-safe, compiled UI layer

### For Users
- **Better Performance**: Native Swift UI responsiveness
- **Native Feel**: macOS-standard interface patterns
- **Enhanced Features**: Platform-specific capabilities
- **Reliability**: Compiled UI with runtime Python backend