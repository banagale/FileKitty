import tomllib
from pathlib import Path

from PyQt5.QtCore import QLibraryInfo
from setuptools import setup

with open(Path(__file__).parent / "pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

meta = pyproject["tool"]["poetry"]
PKG_NAME = meta["name"]
APP_NAME = meta["name"].title()
VERSION = meta["version"]

qt_plugins_dir = QLibraryInfo.location(QLibraryInfo.PluginsPath)

APP = ["src/filekitty/__main__.py"]
OPTIONS = {
    "argv_emulation": False,
    "packages": ["PyQt5"],
    "iconfile": "src/filekitty/resources/icon/FileKitty-icon.icns",
    "plist": {
        "CFBundleIdentifier": f"com.banagale.{PKG_NAME}",
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
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
    "resources": [
        qt_plugins_dir,
        "src/filekitty/resources/icon",
    ],
    "excludes": ["test", "tests", "unittest", "tkinter", "doctest"],
}

setup(
    app=APP,
    name=PKG_NAME,
    version=VERSION,
    data_files=[],
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
