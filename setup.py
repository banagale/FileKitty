from setuptools import setup

APP = ["filekitty/app.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "packages": ["PyQt5"],
    "iconfile": "assets/icon/FileKitty-icon.icns",
    "plist": {
        "CFBundleIdentifier": "com.banagale.filekitty",
        "CFBundleName": "FileKitty",
        "CFBundleDisplayName": "FileKitty",
        "CFBundleShortVersionString": "0.2.0",
        "CFBundleVersion": "0.2.0",
        "CFBundlePackageType": "APPL",
        "NSHighResolutionCapable": True,
        "CFBundleIconFile": "FileKitty-icon.icns",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "All Files",
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Alternate",
                "LSItemContentTypes": ["public.data"],
                "CFBundleTypeIconFile": "FileKitty-icon.icns",
            }
        ],
    },
    "includes": ["sip", "PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets"],
    "resources": [
        "/Users/rob/Library/Caches/pypoetry/virtualenvs/filekitty-YKgFKg7N-py3.12/lib/python3.12/site-packages/PyQt5/Qt5/plugins"
    ],
    "excludes": ["test", "tests", "unittest", "tkinter", "doctest"],
}

setup(
    app=APP,
    name="FileKitty",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
