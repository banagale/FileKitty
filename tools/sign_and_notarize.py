#!/usr/bin/env python3
"""
Build FileKitty.app, sign every Mach‑O binary with the correct entitlement scope, (optionally) notarize, then create a
DMG via **create-dmg**.

Signing strategy
----------------
•  All \*.dylib / framework binaries / .so  -> signed **without** entitlements.
•  Launcher  Contents/MacOS/Filekitty       -> signed **with** entitlements.
•  Outer bundle                             -> sealed with the same entitlements.

DMG creation uses **create-dmg** with --skip-jenkins so that no AppleScript touches the launcher after it is signed.

**Important change (2025‑06‑12)**
The staging copy now preserves symlinks (`symlinks=True`) and keeps times/permissions (`copy_function=shutil.copy2`).
This prevents hash mismatches that broke the code signature after copying.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths & constants
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
STAGING = ROOT / "release/FileKitty-Staging"
APP_BUNDLE = DIST / "FileKitty.app"
LAUNCHER = APP_BUNDLE / "Contents/MacOS/Filekitty"  # <- lower-case k
DMG_PATH = DIST / "FileKitty.dmg"

DMG_SETTINGS = ROOT / "tools/dmg_settings.json"
ENTITLEMENTS = ROOT / "tools/entitlements.plist"
NOTARY_PROFILE = "NotaryProfile"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def run(cmd: list[str] | str, *, check: bool = True) -> None:
    """Run shell command, echo first."""
    if isinstance(cmd, str):
        cmd = [cmd]
    cmd = [str(c) for c in cmd]
    print("$", " ".join(cmd))
    res = subprocess.run(cmd, check=check)
    if check and res.returncode:
        sys.exit(res.returncode)


def developer_id_hash() -> str:
    """Return the first Developer ID Application hash found in the keychain."""
    cmd = "security find-identity -p codesigning -v | awk '/Developer ID Application/ {print $2; exit}'"
    hash_ = subprocess.check_output(["sh", "-c", cmd], text=True).strip()
    if not hash_:
        sys.exit("✖ Developer‑ID certificate not found in keychain.")
    return hash_


CERT_ID = developer_id_hash()


def is_macho(path: Path) -> bool:
    """Return True if *path* looks like a Mach‑O binary."""
    try:
        return "Mach-O" in subprocess.check_output(["file", "-b", str(path)], text=True)
    except subprocess.CalledProcessError:
        return False


# --------------------------------------------------------------------------- #
# Signing helpers
# --------------------------------------------------------------------------- #


def sign_binaries_inside_out(app: Path) -> None:
    """Sign every Mach‑O in depth‑first order."""
    if not ENTITLEMENTS.exists():
        sys.exit(f"✖ Entitlements plist missing: {ENTITLEMENTS}")

    print("✍️  Signing Mach‑O binaries (inside‑out)…")
    machos = sorted(
        [p for p in app.rglob("*") if p.is_file() and is_macho(p)],
        key=lambda p: len(p.parts),
        reverse=True,
    )

    for p in machos:
        cmd: list[str] = [
            "codesign",
            "--force",
            "--options",
            "runtime",
            "--timestamp",
        ]

        if p == LAUNCHER:
            print(f"   ↳ EXECUTABLE with entitlements  : {p.relative_to(ROOT)}")
            cmd += ["--entitlements", str(ENTITLEMENTS)]
        else:
            print(f"   ↳ LIB/FRAMEWORK                : {p.relative_to(ROOT)}")

        cmd += ["--sign", CERT_ID, str(p)]
        run(cmd)


def sign_outer_bundle(app: Path) -> None:
    """Seal the .app bundle with entitlements."""
    print("✍️  Sealing outer bundle…")
    run(
        [
            "codesign",
            "--force",
            "--options",
            "runtime",
            "--timestamp",
            "--entitlements",
            str(ENTITLEMENTS),
            "--sign",
            CERT_ID,
            str(app),
        ]
    )


# --------------------------------------------------------------------------- #
# DMG creation
# --------------------------------------------------------------------------- #


def load_dmg_settings() -> dict:
    with DMG_SETTINGS.open() as fp:
        return json.load(fp)


def create_dmg(settings: dict, *, skip_sign: bool, skip_notarize: bool) -> None:
    """Stage the bundle, optionally sign/notarize the DMG, and build it with *create‑dmg*."""
    if DMG_PATH.exists():
        DMG_PATH.unlink()

    # --- Stage bundle (🚨 preserve symlinks) --------------------------------
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)

    staged_app = STAGING / APP_BUNDLE.name
    shutil.copytree(
        APP_BUNDLE,
        staged_app,
        symlinks=True,
        copy_function=shutil.copy2,
    )

    # Verify signature after copy
    print("\n🔍 Verifying signature of staged bundle…")
    run(["codesign", "--verify", "--deep", "--strict", "-vv", str(staged_app)])

    # --- Build create-dmg command ------------------------------------------
    cmd: list[str] = [
        "create-dmg",
        "--volname",
        settings["title"],
        "--background",
        settings["background"],
        "--window-size",
        str(settings["window"]["size"]["width"]),
        str(settings["window"]["size"]["height"]),
        "--icon-size",
        str(settings["icon-size"]),
        "--skip-jenkins",  # critical: avoid Finder AppleScript touching launcher
    ]

    # Icons / links
    for item in settings["contents"]:
        if item["type"] == "file":
            cmd += ["--icon", item["path"], str(item["x"]), str(item["y"])]
        elif item["type"] == "link" and item["path"] == "/Applications":
            cmd += ["--app-drop-link", str(item["x"]), str(item["y"])]

    # Sign & notarize DMG
    if not skip_sign:
        cmd += ["--codesign", CERT_ID]
    if not skip_sign and not skip_notarize:
        cmd += ["--notarize", NOTARY_PROFILE]

    cmd += [str(DMG_PATH), str(STAGING)]
    run(cmd)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-sign", action="store_true", help="Skip ALL codesigning")
    ap.add_argument("--no-notarize", action="store_true", help="Skip notarization")
    return ap.parse_args()


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> None:
    args = parse_args()

    if not APP_BUNDLE.exists():
        sys.exit(f"✖ Bundle not found: {APP_BUNDLE}")

    # -- signing --------------------------------------------------------------
    if not args.no_sign:
        sign_binaries_inside_out(APP_BUNDLE)
        sign_outer_bundle(APP_BUNDLE)

        print("\n🔍 Local verification …")
        run(["codesign", "--verify", "--deep", "--strict", "-vv", str(APP_BUNDLE)])
    else:
        print("⚠️  --no-sign active — skipping all codesign steps")

    # -- DMG ------------------------------------------------------------------
    print("\n📦 Creating DMG …")
    create_dmg(load_dmg_settings(), skip_sign=args.no_sign, skip_notarize=args.no_notarize)

    # -- summary --------------------------------------------------------------
    if not args.no_sign and not args.no_notarize:
        msg = "DMG built, signed, notarized, stapled."
    elif not args.no_sign and args.no_notarize:
        msg = "DMG built & signed (notarization skipped)."
    else:
        msg = "Unsigned DMG built for layout preview."
    print(f"\n✅ {msg}")


if __name__ == "__main__":
    main()
