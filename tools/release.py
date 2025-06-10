#!/usr/bin/env python3
# tools/release.py ── One-shot release helper for FileKitty
#
#   • bumps version in pyproject.toml
#   • tags & pushes    (git)
#   • builds           (py2app)
#   • zips + writes .sha256
#   • uploads release  (gh)
#   • edits + commits homebrew-filekitty formula
#
# Requirements:  git, poetry, gh (logged-in), shasum
# Usage:  poetry run filekitty-release [--dry-run]
# ---------------------------------------------------------------------------


import argparse
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

# --- Paths & constants -------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FORMULA_PATH = ROOT.parent / "homebrew-filekitty/Formula/filekitty.rb"
REPO = "banagale/FileKitty"
ZIP_TEMPLATE = "FileKitty-{ver}.zip"  # ⚠ no “v” prefix → matches formula
REQUIRED_TOOLS = ["git", "poetry", "gh", "shasum"]


# --- Utility wrappers --------------------------------------------------------
def run(cmd: list[str] | str, *, capture: bool = True, check: bool = True) -> str:
    if isinstance(cmd, str):
        cmd = cmd.split()
    try:
        res = subprocess.run(cmd, check=check, capture_output=capture, text=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"\n✖ Command failed: {' '.join(cmd)}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)


def ensure_tools() -> None:
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing:
        print("✖ Missing required tools:", ", ".join(missing))
        sys.exit(1)


# --- Version helpers ---------------------------------------------------------
def current_pyproject_ver() -> str:
    with (ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["tool"]["poetry"]["version"]


def latest_git_tag() -> str | None:
    out = run(["git", "tag", "--list", "v*", "--sort=-v:refname"])
    tag = out.splitlines()[0] if out else None
    return tag[1:] if tag and tag.startswith("v") else tag


def formula_ver_sha() -> tuple[str | None, str | None]:
    if not FORMULA_PATH.exists():
        return None, None
    txt = FORMULA_PATH.read_text()
    ver_m = re.search(r'url ".+/v(?P<ver>\d+\.\d+\.\d+)/FileKitty-(?P=ver)\.zip"', txt)
    sha_m = re.search(r'sha256 "([a-f0-9]{64})"', txt)
    return (ver_m.group("ver") if ver_m else None, sha_m.group(1) if sha_m else None)


def bump_patch(ver: str) -> str:
    major, minor, patch = map(int, ver.split("."))
    return f"{major}.{minor}.{patch + 1}"


# --- Simple git helpers ------------------------------------------------------
def git_has_changes(path: Path) -> bool:
    return run(["git", "diff", "--quiet", "--", str(path)], check=False) != ""


def git_add_commit_push(path: Path, msg: str) -> None:
    if git_has_changes(path):
        run(["git", "add", str(path)])
        run(["git", "commit", "-m", msg])
        run(["git", "push"])
        print(f"✔ Git commit: {msg}")
    else:
        print("✔ No changes to commit.")


# --- Release steps -----------------------------------------------------------
def set_pyproject_version(new: str) -> None:
    pp = ROOT / "pyproject.toml"
    txt = pp.read_text().splitlines()
    txt = [f'version = "{new}"' if line.startswith("version = ") else line for line in txt]
    pp.write_text("\n".join(txt) + "\n")
    git_add_commit_push(pp, f"chore(release): bump version to {new}")


def create_tag(ver: str) -> None:
    tag = f"v{ver}"
    if tag in run(["git", "tag"]).split():
        print(f"✔ Tag {tag} already exists")
        return
    run(["git", "tag", tag])
    run(["git", "push", "origin", tag])
    print(f"✔ Pushed tag {tag}")


def build_app() -> None:
    run(["poetry", "run", "python", "setup.py", "py2app"])
    print("✔ Built FileKitty.app")


def make_zip(ver: str) -> Path:
    DIST.mkdir(exist_ok=True)
    z = DIST / ZIP_TEMPLATE.format(ver=ver)
    if z.exists():
        z.unlink()
    shutil.make_archive(str(z).removesuffix(".zip"), "zip", DIST, "FileKitty.app")
    print(f"✔ Zipped → {z.name}")
    return z


def write_sha_file(zip_path: Path) -> Path:
    digest = run(["shasum", "-a", "256", str(zip_path)]).split()[0]
    sha_path = zip_path.with_suffix(".zip.sha256")
    sha_path.write_text(f"{digest}  {zip_path.name}\n")
    print(f"✔ sha256 → {sha_path.name}")
    return sha_path


def update_formula(ver: str, digest: str) -> None:
    if not FORMULA_PATH.exists():
        print("✖ Formula file missing.")
        sys.exit(1)
    repo_root = run(["git", "-C", str(FORMULA_PATH.parent.parent), "rev-parse", "--show-toplevel"])
    txt = FORMULA_PATH.read_text()
    txt = re.sub(
        r'url ".+/v\d+\.\d+\.\d+/FileKitty-\d+\.\d+\.\d+\.zip"',
        f'url "https://github.com/{REPO}/releases/download/v{ver}/FileKitty-{ver}.zip"',
        txt,
    )
    txt = re.sub(r'sha256 "[a-f0-9]{64}"', f'sha256 "{digest}"', txt)
    FORMULA_PATH.write_text(txt)
    run(["git", "-C", repo_root, "add", str(FORMULA_PATH)])
    run(["git", "-C", repo_root, "commit", "-m", f"formula: FileKitty {ver}"])
    run(["git", "-C", repo_root, "push"])
    print("✔ Homebrew formula updated")


def gh_release(ver: str, asset: Path, notes: str) -> None:
    tag = f"v{ver}"
    size_mb = asset.stat().st_size / (1024 * 1024)
    print(f"⏳ Uploading {asset.name} ({size_mb:.1f} MB) to GitHub release… please wait.")
    run(["gh", "release", "create", tag, str(asset), "--title", tag, "--notes", notes, "--verify-tag"])
    print("✔ GitHub release published")


# --- Main --------------------------------------------------------------------
def main() -> None:
    ensure_tools()

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="simulate only")
    args = ap.parse_args()

    pv = current_pyproject_ver()
    tv = latest_git_tag()
    fv, _ = formula_ver_sha()

    print(f"pyproject  : {pv}")
    print(f"last tag   : {tv or '(none)'}")
    print(f"formula    : {fv or '(none)'}")

    # Decide next version -----------------------------------------------------
    if pv == tv == fv:
        nxt_default = bump_patch(pv)
        ans = input(f"Next version [{nxt_default}]: ").strip()
        next_ver = ans or nxt_default
    else:
        print("⚠ Version mismatch among sources.")
        ans = input(f"Proceed with pyproject version ({pv})? [y/N] ").lower()
        if ans != "y":
            sys.exit(1)
        next_ver = pv

    if args.dry_run:
        print(f"(dry-run) would release {next_ver}")
        return

    # Actual release ----------------------------------------------------------
    set_pyproject_version(next_ver)
    create_tag(next_ver)
    build_app()
    zip_path = make_zip(next_ver)
    sha256_path = write_sha_file(zip_path)
    sha_val = sha256_path.read_text().split()[0]
    update_formula(next_ver, sha_val)
    gh_release(next_ver, zip_path, f"FileKitty {next_ver} automated release")

    print("\n🎉 Done!  Homebrew can now be updated after CI bots pick up the formula.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n✖ Interrupted")
        sys.exit(1)
