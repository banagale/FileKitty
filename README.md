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
3. Click ***Open** and files will be added to the text area.
4. Select, Copy to clipboard and paste into your prompt:
   <img src="https://github.com/user-attachments/assets/d5a97ee1-4981-4222-bb1f-3993bff9adcb" width="441">

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
