from PyQt5.QtCore import QLibraryInfo
from setuptools import setup

# Dynamically find the Qt plugin directory
qt_plugins_dir = QLibraryInfo.location(QLibraryInfo.PluginsPath)

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
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "All Files",
                "CFBundleTypeRole": "Editor",
                "LSHandlerRank": "Alternate",
                "LSItemContentTypes": ["public.data"],
            }
        ],
    },
    "includes": ["sip", "PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets"],
    "resources": [qt_plugins_dir],
    "excludes": ["test", "tests", "unittest", "tkinter", "doctest"],
}

setup(
    app=APP,
    name="FileKitty",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
