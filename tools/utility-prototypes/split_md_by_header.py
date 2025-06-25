#!/usr/bin/env python3
"""
split_md_by_header.py

Split a long Markdown file into chunks that are at most `max_lines`
lines long, cutting only at header lines (lines whose first non-space
character is "#").

Usage:
    python split_md_by_header.py path/to/longfile.md --out-dir ./chunks --max-lines 2700
"""

import argparse
from pathlib import Path


def find_header_indices(lines: list[str]) -> list[int]:
    """Return indices of all lines that start with '#'."""
    return [idx for idx, line in enumerate(lines) if line.lstrip().startswith("#")]


def write_chunk(lines: list[str], part_no: int, total_parts: int, stem: str, out_dir: Path) -> None:
    """Write a chunk to disk with the format part_x_of_y and a part header inside."""
    out_dir.mkdir(parents=True, exist_ok=True)
    outfile = out_dir / f"{stem}_part_{part_no:02d}_of_{total_parts:02d}.md"
    header = f"<!-- Part {part_no} of {total_parts} -->\n\n"
    outfile.write_text(header + "".join(lines), encoding="utf-8")
    print(f"Wrote {outfile} ({len(lines)} lines + header)")


def split_markdown(input_path: Path, out_dir: Path, max_lines: int = 2700) -> None:
    text = input_path.read_text(encoding="utf-8").splitlines(keepends=True)
    headers = find_header_indices(text)

    if not headers or len(text) <= max_lines:
        write_chunk(text, 1, 1, input_path.stem, out_dir)
        return

    # Compute cut points
    cut_indices = [0]
    for idx in headers[1:]:
        if idx - cut_indices[-1] > max_lines:
            cut_indices.append(idx)
    cut_indices.append(len(text))  # final boundary

    total_parts = len(cut_indices) - 1
    for part_no in range(1, total_parts + 1):
        start = cut_indices[part_no - 1]
        end = cut_indices[part_no]
        write_chunk(text[start:end], part_no, total_parts, input_path.stem, out_dir)


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
