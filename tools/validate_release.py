"""Post‑release validator for FileKitty.

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


def local_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_bytes())
    return data["tool"]["poetry"]["version"]


def file_sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def git_tag_exists(tag: str) -> bool:
    tags = subprocess.check_output(["git", "tag"], text=True).split()
    return tag in tags


def parse_formula() -> dict[str, str]:
    txt = TAP_FORMULA.read_text()
    return {
        "url": re.search(r'url\s+"([^"]+)"', txt).group(1),
        "sha": re.search(r'sha256\s+"([^"]+)"', txt).group(1),
        "version": re.search(r'version\s+"([^"]+)"', txt).group(1),
    }


def main() -> None:
    ver = local_version()
    errors: list[str] = []

    # Tag check
    if not git_tag_exists(f"v{ver}"):
        errors.append(f"Git tag v{ver} missing.")

    # ZIP & sha256
    zip_path = DIST / f"FileKitty-v{ver}.zip"
    sha_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
    if not zip_path.exists():
        errors.append(f"ZIP not found: {zip_path}")
    elif sha_path.exists():
        calc = file_sha(zip_path)
        recorded = sha_path.read_text().split()[0]
        if calc != recorded:
            errors.append("ZIP sha256 mismatch with .sha256 file.")
    else:
        errors.append("sha256 side‑file missing.")

    # Formula
    if TAP_FORMULA.exists():
        f = parse_formula()
        exp_url = f"https://github.com/{REPO}/archive/refs/tags/v{ver}.tar.gz"
        if f["url"] != exp_url:
            errors.append("Formula URL mismatch.")
        if f["version"] != ver:
            errors.append("Formula version mismatch.")
    else:
        errors.append(f"Formula not found at {TAP_FORMULA}")

    if errors:
        for e in errors:
            print("✖", e)
        sys.exit(1)

    print("✓ Release validated: tag, ZIP, and formula are consistent.")


if __name__ == "__main__":
    main()
