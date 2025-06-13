#!/usr/bin/env python3
"""
Build, sign, **harden**, notarize, and package FileKitty for distribution.

Key features
------------
* Stage **first** (with `ditto`) so nothing mutates after signing.
* Preserve resource forks, permissions, *and* symlinks (Apple‑recommended).
* Two‑phase verification:
  – Codesign deep/strict check.
  – *Optional* Gatekeeper assessment that no longer aborts when the app is **expected** to be un‑notarized.
* Clear CLI flags: `--no-sign`, `--no-notarize`, and `--no-gatekeeper`.

The script lives under `tools/packaging/` to keep the repo root clean.
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
ROOT = Path(__file__).resolve().parent.parent.parent  # …/tools/packaging/ → repo root
DIST = ROOT / "dist"
STAGING = ROOT / "build/FileKitty-Staging"
APP_BUNDLE = DIST / "FileKitty.app"
LAUNCHER = APP_BUNDLE / "Contents/MacOS/Filekitty"  # lower‑case k
DMG_PATH = DIST / "FileKitty.dmg"

DMG_SETTINGS = ROOT / "tools/packaging/dmg_settings.json"
ENTITLEMENTS = ROOT / "tools/packaging/entitlements.plist"
NOTARY_PROFILE = "NotaryProfile"  # set up once with:  xcrun notarytool store-credentials …


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def run(cmd: list[str] | str, *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a shell command; echo first. Returns the CompletedProcess."""
    if isinstance(cmd, str):
        cmd = [cmd]
    cmd = [str(c) for c in cmd]
    print("$", " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, capture_output=capture)


def developer_id_hash() -> str:
    awk = "security find-identity -p codesigning -v | awk '/Developer ID Application/ {print $2; exit}'"
    h = subprocess.check_output(["sh", "-c", awk], text=True).strip()
    if not h:
        sys.exit("✖ Developer‑ID certificate not found in keychain.")
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
    """Sign every Mach‑O in depth‑first order; entitlements only on the launcher."""
    if not ENTITLEMENTS.exists():
        sys.exit(f"✖ Entitlements plist missing: {ENTITLEMENTS}")

    print("✍️  Signing Mach‑O binaries (inside‑out) …")
    machos = sorted(
        (p for p in app.rglob("*") if p.is_file() and is_macho(p)),
        key=lambda p: len(p.parts),
        reverse=True,
    )

    for p in machos:
        cmd = [
            "codesign",
            "--force",
            "--options",
            "runtime",
            "--timestamp",
        ]

        if p == LAUNCHER:
            print(f"   ↳ EXECUTABLE with entitlements : {p.relative_to(ROOT)}")
            cmd += ["--entitlements", str(ENTITLEMENTS)]
        else:
            print(f"   ↳ LIB / FRAMEWORK             : {p.relative_to(ROOT)}")

        cmd += ["--sign", CERT_ID, str(p)]
        run(cmd)


def sign_outer_bundle(app: Path) -> None:
    print("✍️  Sealing outer bundle …")
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
# Verification helpers
# --------------------------------------------------------------------------- #


def verify_codesign(app: Path) -> None:
    print("🔍  codesign deep/strict verify …")
    run(["codesign", "--verify", "--deep", "--strict", "-vv", str(app)])


def verify_with_gatekeeper(app: Path, expect_notarized: bool) -> None:
    """Assess with Gatekeeper (spctl). Do **not** abort when rejection is expected."""
    print("🔒  Gatekeeper assessment …")
    proc = run(["spctl", "-vvv", "--assess", "--type", "exec", str(app)], check=False, capture=True)

    if proc.returncode == 0:
        print("   Gatekeeper: ✅ accepted (notarized)")
        if not expect_notarized:
            print("   ⚠️  Was *not* expecting acceptance yet (already notarized?).")
    else:
        print("   Gatekeeper: 🚫 rejected (", proc.stderr.strip() or proc.stdout.strip(), ")")
        if expect_notarized:
            sys.exit("✖ Gatekeeper rejected app **after** notarization.")


# --------------------------------------------------------------------------- #
# DMG creation helpers
# --------------------------------------------------------------------------- #


def load_dmg_settings() -> dict:
    with DMG_SETTINGS.open() as fp:
        return json.load(fp)


def ditto_copy(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ditto",
            "--rsrc",
            "--extattr",
            "--acl",
            str(src),
            str(dst),
        ]
    )


def create_dmg(settings: dict, *, sign: bool, notarize: bool) -> None:
    DMG_PATH.unlink(missing_ok=True)

    # Stage fresh bundle
    if STAGING.exists():
        shutil.rmtree(STAGING)
    (STAGING / "Applications").mkdir(parents=True, exist_ok=True)  # for DMG layout
    staged_app = STAGING / APP_BUNDLE.name
    print("📦  Staging bundle via ditto …")
    ditto_copy(APP_BUNDLE, staged_app)

    # Sign *staged* bundle (outer only, Mach‑Os already signed)
    sign_outer_bundle(staged_app)
    verify_codesign(staged_app)

    # DMG build
    cmd = [
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
        "--skip-jenkins",
    ]
    for item in settings["contents"]:
        if item["type"] == "file":
            cmd += ["--icon", item["path"], str(item["x"]), str(item["y"])]
        elif item["type"] == "link" and item["path"] == "/Applications":
            cmd += ["--app-drop-link", str(item["x"]), str(item["y"])]

    if sign:
        cmd += ["--codesign", CERT_ID]
    if sign and notarize:
        cmd += ["--notarize", NOTARY_PROFILE]

    cmd += [str(DMG_PATH), str(STAGING)]
    run(cmd)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-sign", action="store_true", help="Skip **all** codesigning")
    ap.add_argument("--no-notarize", action="store_true", help="Skip notarization (implies Gatekeeper reject)")
    ap.add_argument("--no-gatekeeper", action="store_true", help="Skip Gatekeeper assessment steps")
    return ap.parse_args()


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def main() -> None:
    args = parse_args()

    if not APP_BUNDLE.exists():
        sys.exit(f"✖ Bundle not found: {APP_BUNDLE}")

    # 1. Sign Mach‑Os **inside original build**
    if not args.no_sign:
        sign_binaries_inside_out(APP_BUNDLE)
        sign_outer_bundle(APP_BUNDLE)
        verify_codesign(APP_BUNDLE)
    else:
        print("⚠️  --no-sign active — skipping signing steps")

    # 2. Pre‑notarization Gatekeeper (expect reject)
    if not args.no_gatekeeper:
        verify_with_gatekeeper(APP_BUNDLE, expect_notarized=False)

    # 3. Build DMG (sign + optional notarize)
    print("\n💽  Creating DMG …")
    create_dmg(
        load_dmg_settings(),
        sign=not args.no_sign,
        notarize=not args.no_notarize and not args.no_sign,
    )

    # 4. Post‑process summary
    if args.no_sign:
        msg = "Unsigned DMG built for layout preview."
    elif args.no_notarize:
        msg = "DMG built & signed (notarization skipped)."
    else:
        msg = "DMG built, signed, notarized, stapled."
    print(f"\n✅ {msg}")

    # 5. Post‑notarization Gatekeeper (only meaningful when signed+notarized)
    if (not args.no_gatekeeper) and (not args.no_sign) and (not args.no_notarize):
        print("\n🔒  Re‑checking Gatekeeper after notarization …")
        verify_with_gatekeeper(APP_BUNDLE, expect_notarized=True)


if __name__ == "__main__":
    main()
