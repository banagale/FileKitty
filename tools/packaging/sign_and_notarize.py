#!/usr/bin/env python3
"""
Build, sign, harden, notarize, and package FileKitty for distribution.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[2]  # project root
DIST = ROOT / "dist"
BUILD = ROOT / "build"
STAGING = BUILD / "FileKitty-Staging"

APP_BUNDLE = DIST / "FileKitty.app"
LAUNCHER = APP_BUNDLE / "Contents/MacOS/Filekitty"
DMG_PATH = DIST / "FileKitty.dmg"

DMG_SETTINGS = ROOT / "tools/packaging/dmg_settings.json"
ENTITLEMENTS = ROOT / "tools/packaging/entitlements.plist"
NOTARY_PROFILE = "NotaryProfile"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def run(
    cmd: Sequence[str] | str,
    *,
    check: bool = True,
    capture: bool = False,
    cwd: None | Path = None,
) -> subprocess.CompletedProcess[str]:
    if isinstance(cmd, str):
        cmd = [cmd]
    print("$", " ".join(map(str, cmd)))
    return subprocess.run(
        [str(c) for c in cmd],
        check=check,
        text=True,
        capture_output=capture,
        cwd=str(cwd) if cwd else None,
    )


def developer_id_hash() -> str:
    cmd = "security find-identity -p codesigning -v | awk '/Developer ID Application/ {print $2; exit}'"
    h = subprocess.check_output(["sh", "-c", cmd], text=True).strip()
    if not h:
        sys.exit("✖ Developer-ID certificate not found.")
    return h


CERT_ID = developer_id_hash()


def is_macho(path: Path) -> bool:
    try:
        return "Mach-O" in subprocess.check_output(["file", "-b", str(path)], text=True)
    except subprocess.CalledProcessError:
        return False


# --------------------------------------------------------------------------- #
# Signing helpers
# --------------------------------------------------------------------------- #
def sign_binaries_inside_out(app: Path) -> None:
    if not ENTITLEMENTS.exists():
        sys.exit(f"✖ Missing entitlements: {ENTITLEMENTS}")

    binaries = sorted(
        (p for p in app.rglob("*") if p.is_file() and is_macho(p)),
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for bin_path in binaries:
        cmd = ["codesign", "--force", "--options", "runtime", "--timestamp"]
        if bin_path == LAUNCHER:
            cmd += ["--entitlements", str(ENTITLEMENTS)]
        cmd += ["--sign", CERT_ID, str(bin_path)]
        run(cmd)


def sign_outer_bundle(app: Path) -> None:
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


def verify_local_signature(app: Path) -> None:
    run(["codesign", "--verify", "--deep", "--strict", "-vv", str(app)])


def gatekeeper_warn_only(app: Path) -> None:
    res = run(["spctl", "-vvv", "--assess", "--type", "exec", str(app)], check=False, capture=True)
    print("🔒  Gatekeeper:", "accepted" if res.returncode == 0 else "rejected (pre-notarization)")


# --------------------------------------------------------------------------- #
# Staging & DMG
# --------------------------------------------------------------------------- #
def ditto_copy(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    run(["ditto", "--rsrc", "--extattr", "--acl", str(src), str(dst)])


def load_dmg_settings() -> dict:
    with DMG_SETTINGS.open() as fp:
        return json.load(fp)


def create_dmg(settings: dict, *, skip_sign: bool, skip_notarize: bool) -> None:
    if DMG_PATH.exists():
        DMG_PATH.unlink()

    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)

    staged_app = STAGING / APP_BUNDLE.name
    ditto_copy(APP_BUNDLE, staged_app)

    sign_binaries_inside_out(staged_app)
    sign_outer_bundle(staged_app)
    verify_local_signature(staged_app)

    # Remove accidental "Applications" symlink (rare)
    applink = STAGING / "Applications"
    if applink.exists():
        applink.unlink()

    background_abs = (ROOT / settings["background"]).resolve()
    if not background_abs.exists():
        sys.exit(f"✖ Background PNG not found: {background_abs}")

    # -------------------------- create-dmg args --------------------------- #
    args: list[str] = [
        "create-dmg",
        "--volname",
        settings["title"],
        "--background",
        str(background_abs),
        "--window-size",
        str(settings["window"]["size"]["width"]),
        str(settings["window"]["size"]["height"]),
        "--icon-size",
        str(settings["icon-size"]),
    ]

    if "pos" in settings["window"]:
        args += ["--window-pos", str(settings["window"]["pos"]["x"]), str(settings["window"]["pos"]["y"])]

    for item in settings["contents"]:
        if item["type"] == "file" and Path(item["path"]).name.lower() != "applications":
            args += ["--icon", item["path"], str(item["x"]), str(item["y"])]
        elif item["type"] == "link" and item["path"] == "/Applications":
            args += ["--app-drop-link", str(item["x"]), str(item["y"])]

    if not skip_sign:
        args += ["--codesign", CERT_ID]
    if not skip_sign and not skip_notarize:
        args += ["--notarize", NOTARY_PROFILE]

    args += [str(DMG_PATH), str(STAGING)]

    # Critical change: run from ROOT, not STAGING
    run(args, cwd=ROOT)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-sign", action="store_true", help="Skip code-signing")
    ap.add_argument("--no-notarize", action="store_true", help="Skip notarization")
    return ap.parse_args()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    args = parse_args()

    if not APP_BUNDLE.exists():
        sys.exit(f"✖ Bundle not found: {APP_BUNDLE}")

    if not args.no_sign:
        sign_binaries_inside_out(APP_BUNDLE)
        sign_outer_bundle(APP_BUNDLE)
        verify_local_signature(APP_BUNDLE)
        gatekeeper_warn_only(APP_BUNDLE)

    create_dmg(load_dmg_settings(), skip_sign=args.no_sign, skip_notarize=args.no_notarize)

    if not args.no_sign and not args.no_notarize:
        print("\n✅ DMG built, signed, notarized, stapled.")
    elif not args.no_sign and args.no_notarize:
        print("\n✅ DMG built & signed (notarization skipped).")
    else:
        print("\n✅ Unsigned DMG built for layout preview.")


if __name__ == "__main__":
    main()
