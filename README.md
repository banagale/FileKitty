# FileKitty

<img src="https://github.com/banagale/FileKitty/assets/1409710/d7c68e71-5245-499b-8be9-3ca1f88adc1b">
A simple file selection and concatenation tool.

## Features

- Select files from a directory
- Concatenate selected files into a single file
- Save the concatenated file to a directory
- Copy file to clipboard

## Good for

- Concatenating files for use in a single file format
- Pasting file contents into an LLM to provide context to a prompt

## Build

### Prerequisites

 - Poetry is used to manage dependencies and build the app.
 - Refer to the [Poetry documentation](https://python-poetry.org/docs/) for installation instructions.

### Build from source
```bash
poetry install
poetry run python setup.py py2app
``` 

- App should show up in ./dist/FileKitty.app
- Copy to Applications folder
