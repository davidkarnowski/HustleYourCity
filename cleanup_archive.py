#!/usr/bin/env python3
"""
cleanup_archive.py

One-time script to migrate old summary_stats_<timestamp>.json files
from ./data into the new archival structure:

    data/archive/YYYY/MM/summary_json_<YYYY-MM-DD_HH-MM-SS>.json

This script:
- Detects all files matching summary_stats_*.json
- Extracts their timestamp (UTC format inside filename)
- Converts timestamp to new filename style
- Creates year/month dirs inside ./data/archive
- Moves each file into its new location
- Prints a summary of moved files

Run **once** after switching to the new archival system.
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")
ARCHIVE_ROOT = DATA_DIR / "archive"

pattern = re.compile(r"summary_stats_(\d{4}-\d{2}-\d{2}T\d{4})Z\.json$")

def migrate_files():
    moved = 0
    skipped = 0

    for f in DATA_DIR.glob("summary_stats_*.json"):
        match = pattern.search(f.name)
        if not match:
            print(f"❌ Skipping unrecognized file: {f.name}")
            skipped += 1
            continue

        timestamp_str = match.group(1)  # e.g., 2025-10-16T1616
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H%M")
        except Exception:
            print(f"❌ Could not parse timestamp for file: {f.name}")
            skipped += 1
            continue

        # Convert to new filename format
        year = dt.strftime("%Y")
        month = dt.strftime("%m")
        new_timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")

        archive_dir = ARCHIVE_ROOT / year / month
        archive_dir.mkdir(parents=True, exist_ok=True)

        new_path = archive_dir / f"summary_json_{new_timestamp}.json"

        # Move file
        shutil.move(str(f), str(new_path))
        print(f"📦 Moved {f.name} → {new_path}")
        moved += 1

    print("\n--- Migration Summary ---")
    print(f"Moved:   {moved}")
    print(f"Skipped: {skipped}")
    print("-------------------------")

if __name__ == "__main__":
    migrate_files()
