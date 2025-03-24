# FileKitty

<img src="https://github.com/banagale/FileKitty/assets/1409710/d7c68e71-5245-499b-8be9-3ca1f88adc1b" width="200">

A simple file selection and concatenation tool.

## Features

- Select files from a directory
- Concatenate selected files into a single file
- Save the concatenated file to a directory
- Copy file to clipboard

## Good for

- Concatenating files for use in a single file format
- Pasting file contents into an LLM to provide context to a prompt

## How to use it

1. Open the app and click ***Open Files***.
2. Select the files you want to concatenate:  
   <img src="https://github.com/user-attachments/assets/5596d32e-52b3-4791-90eb-32ba0def3162" width="741">
3. Click ***Open*** and files will be added to the text area.
4. Select, copy to clipboard, and paste into your prompt:  
   <img src="https://github.com/user-attachments/assets/d5a97ee1-4981-4222-bb1f-3993bff9adcb" width="441">

**OR**

1. In MacOS Finder, find the files you want to concatenate
2. Open the FileKitty app
3. Drag and drop the files into the app
4. Select, copy to clipboard, and paste into your prompt

## Build

### Prerequisites

- Poetry is used to manage dependencies and build the app.
- Refer to the [Poetry documentation](https://python-poetry.org/docs/) for installation instructions.

### Build from source

```bash
poetry install
poetry run python setup.py py2app
```

- App should show up in `./dist/FileKitty.app`
- Copy to `Applications` folder

## Linting and Formatting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and code formatting.

### Run locally

```bash
make lint       # Check for lint issues
make format     # Format code
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
pre-commit run --all-files  # Optional: check everything right away
```

## Continuous Integration

Linting is enforced via GitHub Actions on every push and pull request.  
The workflow is defined in `.github/workflows/lint.yml`.
