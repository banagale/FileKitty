#!/usr/bin/env python3

import argparse
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
HOMEBREW_FORMULA = ROOT.parent / "homebrew-filekitty/Formula/filekitty.rb"
ZIP_TEMPLATE = "FileKitty-{version}.zip"


def run(cmd, check=True, capture_output=True, text=True):
    try:
        return subprocess.run(cmd, check=check, capture_output=capture_output, text=text).stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd)}")
        print(e)
        return None


def local_version():
    with (ROOT / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    return data["tool"]["poetry"]["version"]


def latest_git_tag():
    try:
        output = run(["git", "tag", "--list", "v*", "--sort=-v:refname"])
        tag = output.splitlines()[0] if output else None
        if tag and tag.startswith("v"):
            return tag[1:]
        return tag
    except Exception:
        return None


def brew_formula_version_and_sha():
    if not HOMEBREW_FORMULA.exists():
        return None, None
    content = HOMEBREW_FORMULA.read_text()
    version_match = re.search(r'url ".+/v(\d+\.\d+\.\d+)\.tar\.gz"', content)
    sha_match = re.search(r'sha256 "([a-f0-9]{64})"', content)
    version = version_match.group(1) if version_match else None
    sha = sha_match.group(1) if sha_match else None
    return version, sha


def bump_patch(version):
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError("Expected semver format x.y.z")
    parts[2] = str(int(parts[2]) + 1)
    return ".".join(parts)


def tag_git_version(version, dry_run=False):
    tag = f"v{version}"
    if dry_run:
        print(f"(dry run) Would tag repo with {tag} and push")
    else:
        print(f"Tagging and pushing {tag}... (this may take a moment)")
        run(["git", "tag", tag])
        run(["git", "push", "origin", tag])
        print(f"✔ Tagged and pushed {tag}")


def build_app_bundle(dry_run=False):
    if dry_run:
        print("(dry run) Would build app using setup.py py2app")
        return
    print("Building .app bundle with py2app... (this may take a moment)")
    run([sys.executable, "setup.py", "py2app"])
    print("✔ App built")


def create_zip(version, dry_run=False):
    app_path = DIST / "FileKitty.app"
    zip_path = DIST / ZIP_TEMPLATE.format(version=version)
    if dry_run:
        print(f"(dry run) Would zip {app_path} to {zip_path}")
        return zip_path
    if not app_path.exists():
        raise FileNotFoundError("App bundle not found at dist/FileKitty.app")
    if zip_path.exists():
        zip_path.unlink()
    print(f"Zipping app bundle to {zip_path}...")
    shutil.make_archive(str(zip_path).removesuffix(".zip"), "zip", DIST, "FileKitty.app")
    print(f"✔ Created zip at {zip_path}")
    return zip_path


def calculate_sha256(zip_path):
    print("Calculating sha256...")
    sha = run(["shasum", "-a", "256", str(zip_path)])
    if not sha:
        raise RuntimeError("Failed to calculate sha256")
    return sha.split()[0]


def print_instructions(version, sha256):
    url = f"https://github.com/banagale/FileKitty/releases/download/v{version}/FileKitty-{version}.zip"
    print("\n---")
    print("Homebrew formula block:")
    print(f'  url "{url}"')
    print(f'  sha256 "{sha256}"')
    print("---\n")
    print("GitHub release steps:")
    print(f"  1. Create a new release for tag `v{version}` on GitHub.")
    print(f"  2. Upload: dist/FileKitty-{version}.zip")
    print("  3. Paste Homebrew formula block above into homebrew-filekitty/Formula/filekitty.rb")
    print("---\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Simulate release process without making changes")
    args = parser.parse_args()

    pyproject_ver = local_version()
    git_tag = latest_git_tag()
    brew_ver, brew_sha = brew_formula_version_and_sha()

    print(f"Local version : {pyproject_ver}")
    print(f"Latest tag    : {git_tag or '(none)'}")
    print(f"Brew formula  : {brew_ver or '(none)'}")

    if pyproject_ver == git_tag == brew_ver:
        suggested = bump_patch(pyproject_ver)
        print(f"✔ All sources in sync. Suggested next version: {suggested}")
        user_input = input(f"Use version {suggested}? [Y/n/custom]: ").strip()
        if not user_input or user_input.lower() == "y":
            next_ver = suggested
        elif user_input.lower() == "n":
            print("Aborted by user.")
            return
        else:
            next_ver = user_input.strip()
        print(f"Proceeding with version: {next_ver}")
        tag_git_version(next_ver, dry_run=args.dry_run)
        build_app_bundle(dry_run=args.dry_run)
        zip_path = create_zip(next_ver, dry_run=args.dry_run)
        if not args.dry_run:
            sha256 = calculate_sha256(zip_path)
            print_instructions(next_ver, sha256)
        else:
            print("(dry run) Skipping sha256 + instructions.")
    else:
        print("✖ Version mismatch detected:")
        if pyproject_ver != git_tag:
            print(f"  - pyproject.toml ({pyproject_ver}) != git tag ({git_tag})")
        if brew_ver and pyproject_ver != brew_ver:
            print(f"  - pyproject.toml ({pyproject_ver}) != Homebrew formula ({brew_ver})")
        print("Please resolve before proceeding with a release.")
        return


if __name__ == "__main__":
    main()
