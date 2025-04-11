# FileKitty

<img src="https://github.com/banagale/FileKitty/assets/1409710/d7c68e71-5245-499b-8be9-3ca1f88adc1b" width="200">

A simple macOS utility to select, combine, and copy file contents, especially useful for providing context to **Large
Language Models (LLMs)** and **Generative AI** coding assistants. Includes history tracking.

## Features

- Select files from a directory or via drag-and-drop from Finder Pycharm (jetbrains IDEs) project navigation, etc.
- Display concatenated content from selected files, formatted for easy copying.
- Smartly extract specific Python classes/functions.
- **Navigate history**: Use Back/Forward buttons to revisit previous file selections and generated text outputs.
- **Detect stale content**: Indicates if file contents have changed on disk since a history state was captured.
- Copy generated text to the clipboard with one click.
- Configurable default directory for file selection.
- Configurable storage location for temporary history snapshots.

## Good for

- **LLM Context**: Easily gathering code snippets or text from multiple files to paste into LLM prompts (like ChatGPT,
  Claude, Gemini, Copilot etc.).
- **Generative AI Coding**: Providing accurate, multi-file context to AI coding tools.
- Quickly combining log files or text snippets.
- Reviewing previous sets of files and their combined content via history.

## How to use it

**Basic Concatenation for LLM Context:**

1. Open the FileKitty app.
2. Click **📂 Select Files** or **drag and drop** the source code or text files you need onto the app window.
   *(Example selecting files)*
   <img src="https://github.com/user-attachments/assets/5596d32e-52b3-4791-90eb-32ba0def3162" width="741">
3. The content from the selected files will appear combined in the main text area, formatted with Markdown code blocks (
   e.g., ```python ... ```).
4. Click **📋 Copy to Clipboard**.
5. Paste the combined content directly into your LLM chat or generative AI prompt.
   *(Example text area and copy button)*
   <img src="https://github.com/user-attachments/assets/b95a981e-673d-4df1-ad2f-cb92cd3fc416" width="800">

**Using History:**

- Each time you change the file selection, Python symbol selection, or refresh, a history state is saved (if the text
  output differs).
- Use the **◀ Back** and **▶ Forward** buttons in the toolbar to step through past states.
- The toolbar shows your current position (e.g., "History 3 of 5").
- An indicator like `(Modified)` or `(Missing Files)` appears if the source files on disk no longer match the state you
  are viewing.

**Selecting Python Symbols:**

- If only Python (`.py`) files are selected, click **🔍 Select Classes/Functions**.
- Choose specific symbols; the text area will update to show only those, plus relevant imports – useful for focusing LLM
  context.

**Refreshing Content:**

- Click **🔄 Refresh** to reload content from the files currently listed. This is useful if you edit files outside the
  app.

## Preferences

- Access via the "FileKitty" menu (Cmd+,).
- **Default 'Select Files' Directory**: Set the starting folder for the file dialog.
- **History Storage Directory**: Choose where FileKitty saves temporary history snapshots. Defaults to the system
  temporary location. Changing this clears existing history.

## Build

### Prerequisites

- Requires macOS.
- [Poetry](https://python-poetry.org/docs/) is used for dependency management and building.

### Build from source

```bash
# Clone the repository
# cd FileKitty
poetry install
poetry run python setup.py py2app
```

- The application bundle (`FileKitty.app`) will be in `./dist/`.
- Copy `FileKitty.app` to your `/Applications` folder.

## Linting and Formatting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and code formatting.

### Run locally

```bash
make lint      # Check for lint issues
make format    # Format code
```

Or using poetry directly:

```bash
poetry run ruff check .
poetry run ruff format .
```

## Contributing

### Pre-commit hooks

This project uses [pre-commit](https://pre-commit.com/) to enforce linting before each commit.

To set it up locally:

```bash
poetry install  # If not already done
pre-commit install
# Optional: check everything right away
pre-commit run --all-files
```

## Continuous Integration

- **Linting**: Enforced via GitHub Actions on every push and pull request. See `.github/workflows/lint.yml`.
- **Build Validation**: Ensures the app builds correctly on macOS. See `.github/workflows/build.yml`.
