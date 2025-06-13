#!/usr/bin/env python3
# tools/validate_release.py ── Post-release checker
#
#   • verifies git tag
#   • verifies dist/ ZIP SHA-256
#   • verifies Homebrew formula URL/version/SHA
#
# Usage:  poetry run filekitty-validate
# ---------------------------------------------------------------------------
"""
NOTE: This script validates the local state of the formula.
Be sure to `git commit && git push` the homebrew-filekitty repo
before assuming the release is valid remotely.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FORMULA = ROOT.parent / "homebrew-filekitty/Formula/filekitty.rb"
REPO = "banagale/FileKitty"


# --- utils -------------------------------------------------------------------
def load_ver() -> str:
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["tool"]["poetry"]["version"]


def tag_exists(tag: str) -> bool:
    return tag in subprocess.check_output(["git", "tag"], text=True).split()


def sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


# --- formula parse -----------------------------------------------------------
URL_RE = re.compile(r'url\s+"(?P<url>https://.+?/v(?P<ver>\d+\.\d+\.\d+)(?:/FileKitty-(?P=ver))?\.(?:zip|tar\.gz))"')
SHA_RE = re.compile(r'sha256\s+"(?P<sha>[a-f0-9]{64})"')


def parse_formula() -> dict[str, str]:
    txt = FORMULA.read_text()
    u = URL_RE.search(txt)
    s = SHA_RE.search(txt)
    if not (u and s):
        raise ValueError("Formula missing url/sha256 lines")
    return {"url": u.group("url"), "ver": u.group("ver"), "sha": s.group("sha")}


# --- main --------------------------------------------------------------------
def main() -> None:
    ver = load_ver()
    errs: list[str] = []

    # Git tag check
    if not tag_exists(f"v{ver}"):
        errs.append("git tag missing")

    # Check for ZIP and compute SHA
    zip_path = DIST / f"FileKitty-{ver}.zip"
    zip_sha = sha(zip_path) if zip_path.exists() else None

    # Check for TAR and compute SHA
    tar_path = ROOT / f"FileKitty-{ver}.tar.gz"
    tar_sha = sha(tar_path) if tar_path.exists() else None

    # Parse formula and validate fields
    if FORMULA.exists():
        f = parse_formula()
        if "tar.gz" in f["url"]:
            expected_url = f"https://github.com/{REPO}/archive/refs/tags/v{ver}.tar.gz"
            if f["url"] != expected_url:
                errs.append("formula URL mismatch")
            if f["ver"] != ver:
                errs.append("formula version mismatch")
            if not tar_sha:
                errs.append("tar.gz not found")
            elif f["sha"] != tar_sha:
                errs.append("formula sha256 differs from tar.gz")
        else:
            expected_url = f"https://github.com/{REPO}/releases/download/v{ver}/FileKitty-{ver}.zip"
            if f["url"] != expected_url:
                errs.append("formula URL mismatch")
            if f["ver"] != ver:
                errs.append("formula version mismatch")
            if not zip_sha:
                errs.append("ZIP not found")
            elif f["sha"] != zip_sha:
                errs.append("formula sha256 differs from ZIP")
    else:
        errs.append("formula file missing")

    # Optional side file check (for ZIP)
    sha_side = zip_path.with_suffix(".zip.sha256")
    if zip_sha and sha_side.exists():
        if sha_side.read_text().split()[0] != zip_sha:
            errs.append(".sha256 side-file mismatch")

    # Final status
    if errs:
        for e in errs:
            print("✖", e)
        sys.exit(1)

    print("✓ Release validated – tag, archive, and Homebrew formula all consistent.")


if __name__ == "__main__":
    main()
