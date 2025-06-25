#!/usr/bin/env python3
"""
split_md_by_header.py

Split a long Markdown file into ≤ max_lines-per-file chunks, cutting only
at header lines (lines that begin with one or more “#” characters).

Usage
-----
$ python split_md_by_header.py path/to/longfile.md --out-dir ./chunks --max-lines 2700
"""

import argparse
from pathlib import Path


def find_header_indices(lines: list[str]) -> list[int]:
    """Return indices of all lines that start with '#'."""
    return [idx for idx, line in enumerate(lines) if line.lstrip().startswith("#")]


def write_chunk(lines: list[str], part_no: int, stem: str, out_dir: Path) -> None:
    """Write a chunk to disk."""
    out_dir.mkdir(parents=True, exist_ok=True)
    outfile = out_dir / f"{stem}_part{part_no:02d}.md"
    outfile.write_text("".join(lines), encoding="utf-8")
    print(f"✏️  Wrote {outfile} ({len(lines)} lines)")


def split_markdown(
    input_path: Path, out_dir: Path, max_lines: int = 2700
) -> None:
    text = input_path.read_text(encoding="utf-8").splitlines(keepends=True)
    headers = find_header_indices(text)

    if not headers or len(text) <= max_lines:
        write_chunk(text, 1, input_path.stem, out_dir)
        return

    part_no, start = 1, 0
    for hdr_idx in headers[1:]:  # skip the first header
        if hdr_idx - start > max_lines:
            write_chunk(text[start:hdr_idx], part_no, input_path.stem, out_dir)
            part_no += 1
            start = hdr_idx

    write_chunk(text[start:], part_no, input_path.stem, out_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Split large Markdown file by header.")
    parser.add_argument("input_file", type=Path, help="Path to the source .md file")
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=Path("output_chunks"),
        help="Directory for the output pieces",
    )
    parser.add_argument(
        "-m",
        "--max-lines",
        type=int,
        default=2700,
        help="Maximum lines per output file",
    )
    args = parser.parse_args()
    split_markdown(args.input_file, args.out_dir, args.max_lines)


if __name__ == "__main__":
    main()
