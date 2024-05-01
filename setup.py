from setuptools import setup

APP = ['filekitty/app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['PyQt5'],
    'iconfile': 'assets/icon/FileKitty-icon.icns',
}

setup(
    app=APP,
    name="FileKitty",
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
