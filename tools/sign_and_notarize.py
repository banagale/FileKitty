#!/usr/bin/env python3
# tools/sign_and_notarize.py – Sign and notarize FileKitty.app, then create signed, notarized DMG

import argparse
import subprocess
import sys
from pathlib import Path

APP_NAME = "FileKitty"
APP_BUNDLE = Path("dist") / f"{APP_NAME}.app"
DMG_PATH = Path("dist") / f"{APP_NAME}.dmg"
DMG_SETTINGS = Path("tools") / "dmg_settings.json"
DEV_ID_APP_CERT = "Developer ID Application: Perch Innovations, Inc. (J8P5B23FK7)"
NOTARY_PROFILE = "NotaryProfile"


def run(cmd: list[str], check: bool = True):
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check)
    if result.returncode != 0:
        sys.exit(result.returncode)


def sign_binaries_within_app(app_path: Path):
    print("\n🔍 Recursively signing embedded binaries...")
    dylibs = list(app_path.rglob("*.so"))
    for binary in dylibs:
        print(f"  ↪ Signing {binary}")
        run(
            [
                "codesign",
                "--force",
                "--options",
                "runtime",
                "--timestamp",
                "--sign",
                DEV_ID_APP_CERT,
                str(binary),
            ]
        )


def sign_app():
    print("\n📝 Signing .app bundle...")
    sign_binaries_within_app(APP_BUNDLE)
    run(
        [
            "codesign",
            "--deep",
            "--force",
            "--options",
            "runtime",
            "--timestamp",
            "--sign",
            DEV_ID_APP_CERT,
            str(APP_BUNDLE),
        ]
    )


def create_dmg():
    print("\n📦 Creating .dmg...")
    if DMG_PATH.exists():
        DMG_PATH.unlink()
    run(["dmgbuild", "-s", str(DMG_SETTINGS), APP_NAME, str(DMG_PATH)])


def sign_dmg():
    print("\n📝 Signing .dmg...")
    run(["codesign", "--sign", DEV_ID_APP_CERT, "--timestamp", "--force", str(DMG_PATH)])


def notarize():
    print("\n☁️ Notarizing with Apple...")
    run(["xcrun", "notarytool", "submit", str(DMG_PATH), "--keychain-profile", NOTARY_PROFILE, "--wait", "--progress"])


def staple():
    print("\n📎 Stapling notarization ticket...")
    run(["xcrun", "stapler", "staple", str(DMG_PATH)])
    run(["xcrun", "stapler", "validate", str(DMG_PATH)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-notarize", action="store_true", help="Skip notarization and stapling")
    args = parser.parse_args()

    if not APP_BUNDLE.exists():
        print(f"✖ Missing: {APP_BUNDLE}")
        sys.exit(1)

    sign_app()
    create_dmg()
    sign_dmg()

    if not args.no_notarize:
        notarize()
        staple()
        print("\n✅ All steps complete. FileKitty.dmg is signed and notarized.")
    else:
        print("\n⚠️ Skipped notarization and stapling. .dmg is signed only.")


if __name__ == "__main__":
    main()
