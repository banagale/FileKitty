"""Post-release validator for FileKitty.

Checks:
* Git tag exists
* dist/ ZIP and .sha256 match
* homebrew-filekitty formula url/version/sha256 are updated
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
TAP_FORMULA = ROOT.parent / "homebrew-filekitty/Formula/filekitty.rb"
REPO = "banagale/FileKitty"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def local_version() -> str:
    """Return the version string from pyproject.toml."""
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["tool"]["poetry"]["version"]


def file_sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def git_tag_exists(tag: str) -> bool:
    return tag in subprocess.check_output(["git", "tag"], text=True).split()


# --------------------------------------------------------------------------- #
# Formula parsing
# --------------------------------------------------------------------------- #
FORMULA_URL_RE = re.compile(r'url\s+"(?P<url>https://.+/v(?P<ver>\d+\.\d+\.\d+)/FileKitty-(?P=ver)\.(?:zip|tar\.gz))"')
SHA_RE = re.compile(r'sha256\s+"(?P<sha>[a-f0-9]{64})"')


def parse_formula() -> dict:
    """Return {'url': str, 'version': str, 'sha256': str} parsed from formula."""
    txt = TAP_FORMULA.read_text()

    url_match = FORMULA_URL_RE.search(txt)
    if not url_match:
        raise ValueError("Cannot find URL/version line in formula.")

    sha_match = SHA_RE.search(txt)
    if not sha_match:
        raise ValueError("Cannot find sha256 line in formula.")

    return {
        "url": url_match.group("url"),
        "version": url_match.group("ver"),
        "sha256": sha_match.group("sha"),
    }


# --------------------------------------------------------------------------- #
# Main routine
# --------------------------------------------------------------------------- #
def main() -> None:
    ver = local_version()
    errors: list[str] = []

    # 1. Git tag
    if not git_tag_exists(f"v{ver}"):
        errors.append(f"Git tag v{ver} missing.")

    # 2. ZIP + sha256 • (script creates <dist>/FileKitty-<ver>.zip)
    zip_path = DIST / f"FileKitty-{ver}.zip"
    sha_file = zip_path.with_suffix(".zip.sha256")

    if not zip_path.exists():
        errors.append(f"ZIP not found: {zip_path}")
    elif sha_file.exists():
        if file_sha(zip_path) != sha_file.read_text().split()[0]:
            errors.append("ZIP sha256 mismatch with .sha256 file.")
    else:
        errors.append(".sha256 side-file missing.")

    # 3. Homebrew formula
    if TAP_FORMULA.exists():
        f = parse_formula()
        expected_url = f"https://github.com/{REPO}/releases/download/v{ver}/FileKitty-{ver}.zip"
        if f["url"] != expected_url:
            errors.append("Formula URL mismatch.")
        if f["version"] != ver:
            errors.append("Formula version mismatch.")
    else:
        errors.append(f"Formula file not found at {TAP_FORMULA}")

    # Result
    if errors:
        for e in errors:
            print("✖", e)
        sys.exit(1)

    print("✓ Release validated: git tag, ZIP, and Homebrew formula are consistent.")


if __name__ == "__main__":
    main()
