# FileKitty [![Homebrew](https://img.shields.io/badge/brew-install-green)](https://github.com/banagale/filekitty#quick-install-macos-via-homebrew)

<img src="https://github.com/banagale/FileKitty/assets/1409710/d7c68e71-5245-499b-8be9-3ca1f88adc1b" width="200">

A macOS utility for selecting, combining, and copying the contents of files — ideal for use with **LLMs and generative AI tools**. FileKitty lets you
grab context from multiple files with one click and keeps a full history of your selections.

---

## Why FileKitty?

LLM tools like **Cursor**, **GitHub Copilot Chat**, and **Claude Code** are powerful — but behind the scenes, they often make API completion requests
using **bloated, overstuffed prompts**. These include entire repos, unrelated files, and boilerplate-heavy context, which can **degrade the quality of
even state-of-the-art models.**

**FileKitty gives you control over the prompt.** It’s a lightweight tool for assembling precise, readable context that pairs perfectly with
interactive (chat-based) LLM workflows — whether you're using **ChatGPT**, **Claude**, **Gemini**, or any number of **local models**.

### FileKitty helps you:

* **For coding:** Select only the files, classes, or functions you're working on — and get direct, targeted suggestions instead of vague completions.
* **For documentation and planning:** Combine real code with Slack threads, meeting notes, or config files to produce accurate explanations, writeups,
  and planning docs.
* **For debugging and support:** Isolate logs, config diffs, and source snippets into a focused prompt — no need to paste in your whole project.

Unlike IDE-native assistants that guess behind the scenes, FileKitty lets you **see and shape exactly what the model sees.** You get cleaner inputs,
smarter outputs, and fewer wasted tokens.

What it lacks in IDE integration, it makes up for in **speed, precision, and higher-quality problem solving.**

---

## Use Cases

- Gather code snippets for LLM prompts (ChatGPT, Claude, Gemini, Copilot, etc.)
- Provide precise multi-file context for generative AI tools
- Combine logs, configs, or structured docs for inspection
- Track and revisit prior file selections and outputs

---

## Quick Install (macOS via Homebrew)

```bash
brew install banagale/filekitty/filekitty
```

### Launch the App

- From Terminal:
  ```bash
  filekitty
  ```
- Or via Finder:
  ```bash
  open /opt/homebrew/opt/filekitty/FileKitty.app
  ```

### Make it a Regular Mac App

To access via Spotlight or Launchpad, copy the app to `/Applications`:

```bash
ditto /opt/homebrew/opt/filekitty/FileKitty.app /Applications/FileKitty.app
```

**Note:** Using `ditto` rather than `cp` preserves the application bundle's icon and metadata.

---

## Manual Build (Alternative)

Install [Poetry](https://python-poetry.org/) and build locally:

```bash
git clone https://github.com/banagale/FileKitty.git
cd FileKitty
poetry install
poetry run python setup.py py2app
```

The app will be created in `./dist/`. Copy it to `/Applications` for full integration.

Manual builds are useful for development or Linux/Windows adaptation.

---

## Example Output

Here’s what FileKitty produces when you drop a folder or select multiple files. The result is a clean, timestamped view of file contents, optionally
preceded by a project folder tree.

Below, we’ve selected three Python files from a project:

<img src="https://github.com/user-attachments/assets/a03bce43-0924-4d95-a91b-84b6c66ccb4a" width="600">

The output looks like this inside FileKitty’s preview pane:

````markdown
# Folder Tree of ~/code/…/FileKitty/src/filekitty

```text
filekitty/
├── core/
│   ├── qt_imports.py
├── resources/
├── ui/
│   ├── __pycache__/
│   ├── components/
│   ├── dialogs.py
│   ├── main_window.py
│   ├── qt_widgets.py
│   ├── text_output_area.py
│   └── tree_settings_dialog.py
├── __main__.py
├── app_logic.py
├── constants.py
└── ...
```

# \~/code/…/filekitty/**main**.py

**Last modified: May 20, 2025 5:07 PM**

```python
from filekitty.app_logic import main

if __name__ == "__main__":
    main()
```

# \~/code/…/filekitty/constants.py

**Last modified: Jun 3, 2025 10:26 AM**

```python
from pathlib import Path

ICON_PATH = str((Path(__file__).parent / "resources/icon/FileKitty-icon.png").resolve())
SETTINGS_FILE_IGNORE_KEY = "mainOutputIgnoreRegex"
...
```

# ~/code/…/filekitty/ui/main_window.py

**Last modified: Jun 5, 2025 12:54 PM**

```python
class FilePicker(QWidget):
    def __init__(self, initial_files=None):
        ...
````

## How to Use

1. **Open the app**
2. **Select Files** or drag-and-drop files from Finder, PyCharm, etc.
3. Combined contents will appear, grouped in Markdown code blocks.
4. Click **Copy to Clipboard** and paste into your LLM or chat.

### History Navigation

- Back/Forward buttons let you navigate prior selections
- Changes to file contents are detected and marked as `(Modified)` or `(Missing Files)`

### Python Symbol Mode

- When `.py` files are selected, use **Select Classes/Functions** to target specific symbols and relevant imports.

### Refreshing

- Click **Refresh** to reload the current selection, useful after editing source files.

### Preferences

Access via **FileKitty → Preferences** (`Cmd+,`):

- **Default Select Directory** – sets initial folder for file dialog
- **History Location** – controls where snapshot state is stored

---

## Developer & Contributor Guide

### Local Setup

```bash
git clone https://github.com/banagale/FileKitty.git
cd FileKitty
poetry install
```

* The app can be manually built using:

  ```bash
  poetry run python setup.py py2app
  ```

  The resulting `.app` bundle appears in `./dist/`.

* Run the app directly with:

  ```bash
  poetry run filekitty
  ```

---

### Prerequisites

Before building or releasing, make sure you have:

* macOS (required for app build)
* [Poetry](https://python-poetry.org/) installed
* **Homebrew** - only required for formula validation using filekitty-validate. Must be available in your PATH.

---

### Release & Validation helpers

FileKitty ships two developer tools for publishing new versions:

| Command                         | What it does                                                                                                                                                                                       |
|---------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `poetry run filekitty-release`  | Interactive release assistant: verifies version consistency, builds the app, zips it, generates a `.sha256`, shows a changelog, tags the release, and outputs GitHub/Homebrew update instructions. |
| `poetry run filekitty-validate` | Post-release checker: ensures the pushed tag exists, the ZIP file matches the hash, and the Homebrew formula matches the release metadata.                                                         |

> Tip: Add `--dry-run` to simulate the release without making changes.

---

### Linting & Formatting

Run linting and formatting tools:

```bash
make lint
make format
```

Or directly with Poetry:

```bash
poetry run ruff check .
poetry run ruff format .
```

---

### Pre-commit Hooks

Set up automatic checks before commits:

```bash
pre-commit install
pre-commit run --all-files
```

---

### Continuous Integration

* GitHub Actions validate builds and style checks on each push.
* See `.github/workflows/` for automation details.

## License

MIT License © Rob Banagale