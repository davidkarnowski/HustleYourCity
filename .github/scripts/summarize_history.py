"""Summarize `git filter-repo --analyze` output for the repo-size cleanup.

Usage: python summarize_history.py <analysis-dir>
Prints a Markdown report: packed size by area, the raw exports kept in
history (count, size, per-month spread) and the size left after dropping them.
"""
import re
import sys
from collections import Counter
from pathlib import Path

LINE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\S+)\s+(.+?)\s*$")
RAW = re.compile(r"^data/service_requests_full_(\d{4}-\d{2})-\d{2}T[^/]*\.json(\.gz)?$")
AREAS = [
    ("raw exports", lambda p: RAW.match(p)),
    ("data/charts", lambda p: p.startswith("data/charts/")),
    ("data/dashboard", lambda p: p.startswith("data/dashboard/")),
    ("data/archive", lambda p: p.startswith("data/archive/")),
    ("data/logs", lambda p: p.startswith("data/logs/")),
    ("data (other)", lambda p: p.startswith("data/")),
    ("everything else", lambda p: True),
]


def mb(n):
    return f"{n / 1e6:,.1f} MB"


def main(analysis_dir):
    rows = []
    for line in (Path(analysis_dir) / "path-all-sizes.txt").read_text().splitlines():
        m = LINE.match(line)
        if m:
            rows.append((int(m[1]), int(m[2]), m[3], m[4]))

    area_packed = Counter()
    area_files = Counter()
    raw_months = Counter()
    raw_present = 0
    for _unpacked, packed, deleted, path in rows:
        for name, test in AREAS:
            if test(path):
                area_packed[name] += packed
                area_files[name] += 1
                break
        m = RAW.match(path)
        if m:
            raw_months[m[1]] += 1
            raw_present += deleted == "<present>"

    total = sum(area_packed.values())
    print("## Packed size by area (all history)\n")
    print("| Area | Paths | Packed | Share |\n|---|---:|---:|---:|")
    for name, _ in AREAS:
        print(f"| {name} | {area_files[name]:,} | {mb(area_packed[name])} | "
              f"{100 * area_packed[name] / max(total, 1):.1f}% |")
    print(f"| **total** | {sum(area_files.values()):,} | **{mb(total)}** | |")
    print(f"\nSize left without raw exports: **{mb(total - area_packed['raw exports'])}**\n")

    print("## Raw exports in history\n")
    print(f"{area_files['raw exports']:,} files, {mb(area_packed['raw exports'])} packed, "
          f"{raw_present} still in the tree at HEAD.\n")
    print("| Month | Files |\n|---|---:|")
    for month in sorted(raw_months):
        print(f"| {month} | {raw_months[month]} |")

    print("\n## Largest 15 directories\n")
    print("```")
    lines = (Path(analysis_dir) / "directories-all-sizes.txt").read_text().splitlines()
    print("\n".join(lines[:17]))
    print("```")


if __name__ == "__main__":
    main(sys.argv[1])
