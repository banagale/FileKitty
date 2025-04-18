# FileKitty

<img src="https://github.com/banagale/FileKitty/assets/1409710/d7c68e71-5245-499b-8be9-3ca1f88adc1b" width="200">

A macOS utility for selecting, combining, and copying the contents of files — ideal for use with **LLMs and generative AI tools**. FileKitty lets you
grab context from multiple files with one click and keeps a full history of your selections.

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

Launch from **Applications** or from terminal with simply: `filekitty`

## Install via build 
See Manual Build section below.

---


## Screenshots

*Select files, preview combined output, copy instantly*

<img src="https://github.com/user-attachments/assets/5596d32e-52b3-4791-90eb-32ba0def3162" width="741">
<img src="https://github.com/user-attachments/assets/b95a981e-673d-4df1-ad2f-cb92cd3fc416" width="800">

---

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

##️ Developer & Contributor Guide

### Manual Build 

Install [Poetry](https://python-poetry.org/):

```bash
git clone https://github.com/banagale/FileKitty.git
cd FileKitty
poetry install
poetry run python setup.py py2app
```

The app bundle will be created in `./dist/`. Copy it to `/Applications` to use it like a regular app.

> Manual builds may assist in testing or adapting for Linux/Windows.

---

### Linting & Formatting

Uses [Ruff](https://docs.astral.sh/ruff/):

```bash
make lint      # Run linter
make format    # Format code

# or directly
poetry run ruff check .
poetry run ruff format .
```

---

### Pre-commit Hooks

Set up local linting before commits:

```bash
pre-commit install
pre-commit run --all-files
```

---

### Continuous Integration

- GitHub Actions validate linting and build on every push
- See `.github/workflows/` for full pipeline

---

## License

MIT License © Rob Banagale
