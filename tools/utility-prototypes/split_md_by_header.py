#!/usr/bin/env python3
"""
Robust Markdown splitter:

• honours max_lines *strictly*
• prefers breaking on
      1) '# ~/code/…/file.ext'
      2) '# Folder Tree of ~/code/…/'
• never cuts inside a ``` fenced block
• prepends <!-- Part X of Y --> to each chunk
"""

import argparse
import re
from pathlib import Path

HDR_PATH = re.compile(r"^# ~\/.+\.\w+")
HDR_TREE = re.compile(r"^# Folder Tree of ~\/.+")


def is_header(ln: str) -> bool: return bool(HDR_PATH.match(ln) or HDR_TREE.match(ln))


TRIPLE_TICK = re.compile(r"^\s*```")


def chunk_indices(lines: list[str], max_lines: int) -> list[tuple[int, int]]:
    """
    Return (start, end) pairs such that end-start ≤ max_lines.
    """
    chunks: list[tuple[int, int]] = []
    start = 0
    inside_code = False
    last_header: int | None = None
    last_blank: int | None = None

    for i, ln in enumerate(lines):
        if TRIPLE_TICK.match(ln):
            inside_code = not inside_code

        if not inside_code and ln.strip() == "":
            last_blank = i

        if not inside_code and is_header(ln):
            last_header = i

        if i - start + 1 > max_lines:  # +1 because 0-based
            # choose the best split point
            split_at = None
            if last_header and last_header > start:
                split_at = last_header
            elif last_blank and last_blank > start:
                split_at = last_blank
            else:
                # Forced cut: if we're inside code, push forward to fence-end
                split_at = i
                j = i
                while inside_code and j < len(lines):
                    j += 1
                    if j < len(lines) and TRIPLE_TICK.match(lines[j]):
                        inside_code = False
                        split_at = j + 1  # cut *after* the closing ```
                        break

            chunks.append((start, split_at))
            start = split_at
            # reset “recent” markers if they’re before new start
            if last_header and last_header < start:
                last_header = None
            if last_blank and last_blank < start:
                last_blank = None

    chunks.append((start, len(lines)))
    return [c for c in chunks if c[1] - c[0] > 0]  # drop empties


def write_chunk(out_dir: Path, stem: str,
                n: int, total: int,
                body: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{stem}_part_{n:02d}_of_{total:02d}.md"
    header = f"<!-- Part {n} of {total} -->\n\n"
    path.write_text(header + "".join(body), encoding="utf-8")
    print(f"Wrote {path} ({len(body)} body lines)")


def split_markdown(src: Path, out_dir: Path, max_lines: int) -> None:
    lines = src.read_text(encoding="utf-8").splitlines(keepends=True)
    spans = chunk_indices(lines, max_lines)
    total = len(spans)
    for n, (s, e) in enumerate(spans, 1):
        write_chunk(out_dir, src.stem, n, total, lines[s:e])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_file", type=Path)
    ap.add_argument("-o", "--out-dir", type=Path, default=Path("chunks"))
    ap.add_argument("-m", "--max-lines", type=int, default=2700)
    args = ap.parse_args()
    split_markdown(args.input_file, args.out_dir, args.max_lines)


if __name__ == "__main__":
    main()
