#!/usr/bin/env python3
"""
tools/release.py – One-button (ish) release assistant for FileKitty.

Requirements
------------
* poetry
* git (with write access to origin)
* gh   (GitHub CLI, authenticated)
* shasum (macOS builtin)

Typical flow
------------
$ poetry run filekitty-release
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
HOMEBREW_FORMULA = ROOT.parent / "homebrew-filekitty/Formula/filekitty.rb"
ZIP_TEMPLATE = "FileKitty-{version}.zip"
REQUIRED_TOOLS = ["poetry", "git", "gh", "shasum"]

# ─── Helpers ───────────────────────────────────────────────────────────────────


def run(cmd: list[str] | str, *, capture: bool = True) -> str:
    """Run a command; abort on failure."""
    if isinstance(cmd, str):
        cmd = cmd.split()

    try:
        res = subprocess.run(
            cmd,
            check=True,
            capture_output=capture,
            text=True,
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"\n✖ Command failed: {' '.join(cmd)}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)


def need_tools() -> None:
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing:
        print("✖ Missing required tools:", ", ".join(missing))
        sys.exit(1)


def pyproject_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    return data["tool"]["poetry"]["version"]


def latest_tag() -> str | None:
    tag = run(["git", "tag", "--list", "v*", "--sort=-v:refname"])
    first = tag.splitlines()[0] if tag else None
    return first[1:] if first and first.startswith("v") else first


def formula_version_sha() -> tuple[str | None, str | None]:
    if not HOMEBREW_FORMULA.exists():
        return None, None
    txt = HOMEBREW_FORMULA.read_text()
    ver_m = re.search(r'url ".+/v(?P<v>\d+\.\d+\.\d+)/FileKitty-(?P=v)\.zip"', txt)
    sha_m = re.search(r'sha256 "([a-f0-9]{64})"', txt)
    return (ver_m.group(1) if ver_m else None, sha_m.group(1) if sha_m else None)


def bump_patch(v: str) -> str:
    major, minor, patch = map(int, v.split("."))
    return f"{major}.{minor}.{patch + 1}"


# ─── Mutating helpers (abort on failure) ───────────────────────────────────────


def git_commit_file(path: Path, msg: str) -> None:
    run(["git", "add", str(path)])
    run(["git", "commit", "-m", msg])
    run(["git", "push"])


def set_pyproject_version(v: str) -> None:
    p = ROOT / "pyproject.toml"
    lines = p.read_text().splitlines()
    new = [f'version = "{v}"' if ln.startswith("version = ") else ln for ln in lines]
    p.write_text("\n".join(new) + "\n")
    git_commit_file(p, f"chore: bump version to {v}")
    print(f"✔ pyproject.toml -> {v}")


def create_tag(v: str) -> None:
    tag = f"v{v}"
    existing = run(["git", "tag"])
    if tag in existing.splitlines():
        print(f"✔ Tag {tag} already exists")
        return
    run(["git", "tag", tag])
    run(["git", "push", "origin", tag])
    print(f"✔ Pushed git tag {tag}")


def build_app() -> None:
    run(["poetry", "run", "python", "setup.py", "py2app"])
    print("✔ Built FileKitty.app")


def archive_app(v: str) -> Path:
    dst = DIST / ZIP_TEMPLATE.format(version=v)
    if dst.exists():
        dst.unlink()
    shutil.make_archive(str(dst).removesuffix(".zip"), "zip", DIST, "FileKitty.app")
    print(f"✔ Archived app -> {dst.name}")
    return dst


def sha256(path: Path) -> str:
    digest = run(["shasum", "-a", "256", str(path)]).split()[0]
    print(f"✔ SHA-256: {digest}")
    return digest


def update_formula(v: str, digest: str) -> None:
    repo_root = run(["git", "-C", str(HOMEBREW_FORMULA.parent.parent), "rev-parse", "--show-toplevel"])
    txt = HOMEBREW_FORMULA.read_text()
    txt = re.sub(
        r'url ".+/v\d+\.\d+\.\d+/FileKitty-\d+\.\d+\.\d+\.zip"',
        f'url "https://github.com/banagale/FileKitty/releases/download/v{v}/FileKitty-{v}.zip"',
        txt,
    )
    txt = re.sub(r'sha256 "[a-f0-9]{64}"', f'sha256 "{digest}"', txt)
    HOMEBREW_FORMULA.write_text(txt)
    run(["git", "-C", repo_root, "add", str(HOMEBREW_FORMULA)])
    run(["git", "-C", repo_root, "commit", "-m", f"formula: FileKitty {v}"])
    run(["git", "-C", repo_root, "push"])
    print("✔ Homebrew formula updated & pushed")


def gh_release(v: str, asset: Path) -> None:
    tag = f"v{v}"
    run(
        [
            "gh",
            "release",
            "create",
            tag,
            str(asset),
            "--title",
            tag,
            "--notes",
            f"FileKitty {tag} release (automated).",
            "--verify-tag",
        ]
    )
    print("✔ GitHub release published")


# ─── Main entry ────────────────────────────────────────────────────────────────


def main() -> None:
    need_tools()

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Do everything but write")
    args = parser.parse_args()

    pv = pyproject_version()
    tv = latest_tag()
    fv, _ = formula_version_sha()

    print(f"Local version : {pv}")
    print(f"Latest tag    : {tv or '(none)'}")
    print(f"Brew formula  : {fv or '(none)'}\n")

    if pv == tv == fv:
        default_next = bump_patch(pv)
        ans = input(f"Suggested next version is {default_next}. Accept? [Y/n/custom] ").strip().lower()
        if ans in ("", "y"):
            next_ver = default_next
        elif ans == "n":
            print("Aborted.")
            return
        else:
            next_ver = ans
    else:
        print("⚠️ Versions mismatch; continuing with pyproject version.")
        next_ver = pv

    if args.dry_run:
        print(f"\n(dry-run) Would release version {next_ver}")
        return

    # 1. pyproject version
    set_pyproject_version(next_ver)
    # 2. tag
    create_tag(next_ver)
    # 3. build + zip
    build_app()
    zip_path = archive_app(next_ver)
    digest = sha256(zip_path)
    # 4. brew & GitHub
    update_formula(next_ver, digest)
    gh_release(next_ver, zip_path)

    # ─── Summary ──────────────────────────────────────────────────────────────
    print(
        f"\n🎉 Release {next_ver} done!\n"
        f"  Homebrew stanza:\n"
        f'    url "https://github.com/banagale/FileKitty/releases/download/v{next_ver}/FileKitty-{next_ver}.zip"\n'
        f'    sha256 "{digest}"\n'
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n✖ Interrupted by user")
        sys.exit(1)
