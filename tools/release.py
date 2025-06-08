#!/usr/bin/env python3
"""
tools/release.py – one-stop (interactive) release assistant for **FileKitty**

What it does – when *not* in --dry-run:
①   bumps *pyproject.toml* version, commits + pushes
②   tags the repo and pushes the tag (skips if tag already exists)
③   builds the `.app` bundle with py2app
④   zips the bundle to dist/FileKitty-vX.Y.Z.zip
⑤   calculates SHA-256
⑥   edits *homebrew-filekitty* formula, commits + pushes
⑦   creates a GitHub release (via `gh`) and uploads the ZIP

Requirements
------------
* git  – repo must be clean and on a branch that can push to *origin*
* poetry
* gh   – authenticated ( `gh auth status` should be green )
* shasum (macOS default)

Usage
-----
poetry run filekitty-release           # full run
poetry run filekitty-release --dry-run # tell me what you *would* do
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

# ── config ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
TAP_FORMULA = ROOT.parent / "homebrew-filekitty/Formula/filekitty.rb"
ZIP_TEMPLATE = "FileKitty-v{version}.zip"
REPO = "banagale/FileKitty"
NEEDED_TOOLS = ["git", "poetry", "gh", "shasum"]

# ── helpers ───────────────────────────────────────────────────────────────────


def run(cmd: list[str] | str, *, capture: bool = True) -> str:
    """Run a subprocess, exit on failure, return stdout."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    try:
        res = subprocess.run(cmd, check=True, capture_output=capture, text=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"\n✖ command failed: {' '.join(cmd)}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)


def need_tools() -> None:
    missing = [t for t in NEEDED_TOOLS if shutil.which(t) is None]
    if missing:
        print("✖ missing tools:", ", ".join(missing))
        sys.exit(1)


def pyproject_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    return data["tool"]["poetry"]["version"]


def latest_tag() -> str | None:
    tags = run(["git", "tag", "--list", "v*", "--sort=-v:refname"])
    first = tags.splitlines()[0] if tags else None
    return first[1:] if first and first.startswith("v") else first


FORMULA_URL_RE = re.compile(r'url ".+/v(?P<ver>\d+\.\d+\.\d+)/FileKitty-(?P=ver)\.zip"')
SHA_RE = re.compile(r'sha256 "([a-f0-9]{64})"')


def formula_version_sha() -> tuple[str | None, str | None]:
    if not TAP_FORMULA.exists():
        return None, None
    txt = TAP_FORMULA.read_text()
    ver = FORMULA_URL_RE.search(txt)
    sha = SHA_RE.search(txt)
    return (ver.group("ver") if ver else None, sha.group(1) if sha else None)


def bump_patch(version: str) -> str:
    major, minor, patch = map(int, version.split("."))
    return f"{major}.{minor}.{patch + 1}"


# ── git / fs mutators ────────────────────────────────────────────────────────


def git_commit(path: Path | str, msg: str) -> None:
    run(["git", "add", str(path)])
    run(["git", "commit", "-m", msg])
    run(["git", "push"])


def set_pyproject_version(new: str) -> None:
    pp = ROOT / "pyproject.toml"
    txt = pp.read_text().splitlines()
    txt = [f'version = "{new}"' if line.startswith("version = ") else line for line in txt]
    pp.write_text("\n".join(txt) + "\n")
    git_commit(pp, f"chore(release): bump version to {new}")
    print(f"✔ pyproject.toml set to {new}")


def tag_repo(ver: str) -> None:
    tag = f"v{ver}"
    existing = run(["git", "tag"])
    if tag in existing.split():
        print(f"✔ git tag {tag} already exists")
        return
    run(["git", "tag", tag])
    run(["git", "push", "origin", tag])
    print(f"✔ pushed git tag {tag}")


def build_app() -> None:
    run(["poetry", "run", "python", "setup.py", "py2app"])
    print("✔ built FileKitty.app")


def zip_app(ver: str) -> Path:
    dst = DIST / ZIP_TEMPLATE.format(version=ver)
    if dst.exists():
        dst.unlink()
    shutil.make_archive(str(dst).removesuffix(".zip"), "zip", DIST, "FileKitty.app")
    print(f"✔ archived to {dst.name}")
    return dst


def sha256(path: Path) -> str:
    digest = run(["shasum", "-a", "256", str(path)]).split()[0]
    print(f"✔ sha256 = {digest}")
    return digest


def update_formula(ver: str, digest: str) -> None:
    if not TAP_FORMULA.exists():
        print("✖ homebrew formula not found; skipping")
        return
    repo_root = run(["git", "-C", str(TAP_FORMULA.parent.parent), "rev-parse", "--show-toplevel"])
    txt = TAP_FORMULA.read_text()
    txt = FORMULA_URL_RE.sub(f'url "https://github.com/{REPO}/releases/download/v{ver}/FileKitty-{ver}.zip"', txt)
    txt = SHA_RE.sub(f'sha256 "{digest}"', txt)
    TAP_FORMULA.write_text(txt)
    run(["git", "-C", repo_root, "add", str(TAP_FORMULA)])
    run(["git", "-C", repo_root, "commit", "-m", f"filekitty {ver}"])
    run(["git", "-C", repo_root, "push"])
    print("✔ homebrew formula updated & pushed")


def gh_release(ver: str, asset: Path) -> None:
    tag = f"v{ver}"
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
            f"FileKitty {tag} automated release",
            "--verify-tag",
        ]
    )
    print("✔ GitHub release published")


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    need_tools()

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print what would happen, do nothing")
    args = ap.parse_args()

    pv = pyproject_version()
    tv = latest_tag()
    fv, _ = formula_version_sha()

    print(f"Local version : {pv}")
    print(f"Latest tag    : {tv or '(none)'}")
    print(f"Homebrew      : {fv or '(none)'}\n")

    # decide next version
    if pv == tv == fv:
        default = bump_patch(pv)
        ans = input(f"next version → {default}   [Y/n/custom] : ").strip().lower()
        if ans in ("", "y"):
            next_ver = default
        elif ans == "n":
            print("aborted.")
            return
        elif ans == "custom":
            next_ver = input("enter custom semver: ").strip()
        else:
            next_ver = ans
    else:
        print("⚠ versions differ; proceeding with pyproject version")
        next_ver = pv
        if input("continue? [y/N] ").strip().lower() != "y":
            print("aborted.")
            return

    if args.dry_run:
        print(f"\n(dry-run) would release {next_ver}")
        return

    # ── release steps ────────────────────────────────────────────────────────
    print("\n— RELEASE START —")
    set_pyproject_version(next_ver)  # 1
    tag_repo(next_ver)  # 2
    build_app()  # 3
    zip_path = zip_app(next_ver)  # 4
    digest = sha256(zip_path)  # 5
    update_formula(next_ver, digest)  # 6
    gh_release(next_ver, zip_path)  # 7
    print("— RELEASE DONE  —")

    print(
        "\n🍻 Homebrew stanza for manual review:\n"
        f'  url "https://github.com/{REPO}/releases/download/v{next_ver}/FileKitty-{next_ver}.zip"\n'
        f'  sha256 "{digest}"\n'
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n✖ interrupted")
        sys.exit(1)
