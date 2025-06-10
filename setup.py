#!/usr/bin/env python3

import tomllib
from pathlib import Path

from PyQt5.QtCore import QLibraryInfo
from setuptools import setup

ROOT = Path(__file__).parent.resolve()
PYPROJECT = ROOT / "pyproject.toml"
ICON = ROOT / "src" / "filekitty" / "resources" / "icon" / "FileKitty-icon.icns"
QT_PLUGINS_DIR = QLibraryInfo.location(QLibraryInfo.PluginsPath)

# Load metadata from pyproject.toml
with PYPROJECT.open("rb") as f:
    meta = tomllib.load(f)["tool"]["poetry"]

PKG_NAME = meta["name"]
APP_NAME = PKG_NAME.title()
VERSION = meta["version"]

APP = ["src/filekitty/__main__.py"]

OPTIONS = {
    "argv_emulation": False,
    "packages": ["PyQt5", "filekitty"],
    "iconfile": str(ICON),
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
        QT_PLUGINS_DIR,
        str(ICON),
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
