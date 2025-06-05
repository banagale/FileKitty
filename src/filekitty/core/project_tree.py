"""Generate a markdown-formatted directory tree for FileKitty."""

import re
from pathlib import Path

from rich.console import Console
from rich.tree import Tree

from filekitty.core.utils import display_path

_MAX_DEPTH = 5  # default


def _add_nodes(current: Tree, path: Path, ignore: re.Pattern, depth: int, max_depth: int):
    """Recursive helper to build Rich.Tree."""
    if depth >= max_depth:
        return
    try:
        for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if ignore.search(str(child)):
                continue
            label = child.name + ("/" if child.is_dir() else "")
            node = current.add(label)
            if child.is_dir():
                _add_nodes(node, child, ignore, depth + 1, max_depth)
    except PermissionError:
        current.add("[permission denied]")


def generate_tree(
    base_path: str,
    ignore_regex: str,
    max_depth: int = _MAX_DEPTH,
    project_root: Path | None = None,
) -> tuple[str, dict]:
    """
    Returns (markdown_block, snapshot_dict).

    snapshot_dict = {
        "base_path": str,
        "ignore_regex": str,
        "rendered": markdown_block,
    }
    """
    base = Path(base_path).expanduser().resolve()
    if not base.is_dir():
        raise ValueError(f"Base path is not a directory: {base}")

    ignore = re.compile(ignore_regex)
    root_tree = Tree(base.name + "/")
    _add_nodes(root_tree, base, ignore, 0, max_depth)

    console = Console(record=True, width=120)
    console.print(root_tree)

    rendered = console.export_text().rstrip()
    md_block = f"# Folder Tree of {display_path(base, project_root, show_ellipsis=True)}\n\n```text\n{rendered}\n```\n"

    disp = display_path(base, project_root, show_ellipsis=True)
    return md_block, {
        "base_path": str(base),
        "base_path_display": disp,
        "ignore_regex": ignore_regex,
        "rendered": md_block,
    }
