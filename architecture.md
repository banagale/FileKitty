# FileKitty Project Architecture

This document describes the modular structure of the FileKitty application, a PyQt5-based GUI tool for extracting and
reformatting code from selected files.

## Overview

The project follows a modular layout with clearly separated concerns:

- **UI components** live under `src/filekitty/ui/`
- **Business logic** starts in `app_logic.py` and drives the app via `__main__.py`
- **Persistent state/history** is managed through `HistoryManager` in `core/`
- **AST-based code parsing and formatting** is handled in `python_parser.py`
- **Utilities** like text detection and path sanitization live in `core/utils.py`
- **Shared constants and settings** are in `constants.py`

---

## Directory Structure

```

src/
└── filekitty/
├── **main**.py                # Entrypoint for launching the app
├── app\_logic.py               # Main application bootstrap and event routing
├── constants.py               # Shared configuration values and settings keys
├── qt\_imports.py              # (Currently unused placeholder)
├── core/                      # Shared logic modules (not UI-dependent)
│   ├── history\_manager.py     # Class to manage snapshot-based file history
│   ├── python\_parser.py       # Parses Python files to extract symbols and code blocks
│   └── utils.py               # File type checks, path sanitization, encoding handling
├── resources/
│   └── icon/                  # Application icon assets
└── ui/                        # All user interface code (PyQt5-based)
├── main\_window\.py         # Core UI layout, interaction logic, and drag-drop handling
├── dialogs.py             # Preferences and class/function selection dialogs
├── qt\_widgets.py          # Custom widgets, like the drag-out button
├── components/            # Future home for split-out UI widgets (e.g. FileList, Toolbar)
└── text\_output\_area.py    # (Currently unused placeholder; pending refactor destination)

```

---

## Execution Flow

1. **`__main__.py`** triggers `app_logic.main()`.
2. **`FileKittyApp`** initializes QApplication and passes CLI args (filtered for files) to `FilePicker`.
3. **`FilePicker` (main_window.py)** sets up the GUI, loads user settings, and handles file operations.
4. Files can be selected, dropped in, or opened via macOS dock.
5. Selected classes/functions are extracted using **`python_parser.py`**.
6. Output is composed in Markdown format and shown in the main text area.
7. **`HistoryManager`** maintains undo/redo state snapshots and checks for stale files.
8. On close, temporary drag-out files and history are cleaned up.

---

## Notes for LLMs

- **Start here:** `src/filekitty/__main__.py` or `app_logic.py` for launch behavior.
- **Edit UI behavior:** go to `ui/main_window.py`, `ui/dialogs.py`, or `ui/qt_widgets.py`.
- **Parse logic issues:** check `core/python_parser.py` (uses AST), and `core/utils.py`.
- **UI refactor targets:** `ui/components/` is the current destination for modular UI splits.
- **History problems or bugs:** investigate `core/history_manager.py`.

---

## Build and Distribution

- **Built using**: `pyproject.toml` + `Poetry`
- **Packaging**: Built artifacts output to `dist/` and `build/`
- **macOS App**: Uses `py2app` via Makefile or `update.sh` for bundling

---

## Future Improvements

- Migrate `text_output_area.py` content to `ui/components/` and remove placeholder
- Add more test coverage and stubbed tests for UI modules
- Integrate auto-save snapshots and UI state persistence