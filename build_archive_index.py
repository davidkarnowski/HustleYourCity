"""Build the archive index the archive viewer reads.

Every pipeline run already archives its stats JSON and the five LLM summaries
in data/archive/YYYY/MM/. This script only *indexes* them; it never copies or
re-renders data, so the repo grows by a few KB per run, not by new pages.

Writes:
  data/archive/index/<YYYY-MM>.json   one entry per run whose Los Angeles date
                                      falls in that month
  data/archive/index/months.json      month list with run counts per day
                                      (drives the calendars)

Normal pipeline use rewrites only the months touched by the last ~2 archive
folders. `--all` rebuilds every month (one-time backfill).
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ARCHIVE_ROOT = Path("data/archive")
INDEX_DIR = ARCHIVE_ROOT / "index"
LA = ZoneInfo("America/Los_Angeles")

JSON_RE = re.compile(r"summary_json_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.json$")
TEXT_RE = re.compile(r"summary_(4_hour|24_hour|7_day|30_day|90_day)_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.txt$")
LABEL_TO_PERIOD = {"4_hour": "4hours", "24_hour": "24hours", "7_day": "7days", "30_day": "30days", "90_day": "90days"}
# The LLM step finishes within minutes of the stats JSON; anything later belongs to another run.
PAIR_WINDOW = timedelta(minutes=45)


def _stamp(s: str) -> datetime:
    # Archive filenames use the runner clock, which is UTC on GitHub Actions.
    return datetime.strptime(s, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scan(folders: list[Path]) -> list[dict]:
    runs, texts = [], []
    for folder in folders:
        for p in sorted(folder.glob("summary_*")):
            if m := JSON_RE.search(p.name):
                runs.append({"path": p, "stamp": _stamp(m.group(1)), "id": m.group(1)})
            elif m := TEXT_RE.search(p.name):
                texts.append({"path": p, "stamp": _stamp(m.group(2)), "period": LABEL_TO_PERIOD[m.group(1)]})
    runs.sort(key=lambda r: r["stamp"])

    entries = []
    for i, run in enumerate(runs):
        nxt = runs[i + 1]["stamp"] if i + 1 < len(runs) else None
        try:
            data = json.loads(run["path"].read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # unreadable snapshot: leave it out of the index rather than show bad numbers
        downloaded = data.get("downloaded_at")
        processed = (data.get("source_update_times") or {}).get("data_processed_at")
        # The windows ("Last 7 Days" …) are measured back from the moment the parse step ran, which is
        # seconds before it wrote this file, so the file's own timestamp is the window end. downloaded_at
        # (when the City export was fetched) is a few minutes earlier and is kept for the page as well.
        window_end = run["stamp"]
        when = datetime.fromisoformat(downloaded.replace("Z", "+00:00")) if downloaded else window_end

        run_texts, fallback = {}, []
        for t in texts:
            if run["stamp"] <= t["stamp"] <= run["stamp"] + PAIR_WINDOW and (nxt is None or t["stamp"] < nxt):
                rel = t["path"].relative_to(ARCHIVE_ROOT).as_posix()
                run_texts[t["period"]] = rel
                if t["path"].read_text(encoding="utf-8").lstrip().startswith("[Note:"):
                    fallback.append(t["period"])

        entries.append({
            "id": run["id"],
            "date_la": window_end.astimezone(LA).strftime("%Y-%m-%d"),
            "window_end": _iso(window_end),
            "downloaded_at": _iso(when),
            "downloaded_at_exact": bool(downloaded),  # early archives lack it; the run time stands in
            "data_processed_at": processed,
            "json": run["path"].relative_to(ARCHIVE_ROOT).as_posix(),
            "texts": run_texts,
            "fallback": sorted(fallback),
        })
    return entries


def write_if_changed(path: Path, obj) -> bool:
    text = json.dumps(obj, indent=1, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False  # no diff, no commit churn
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="rebuild every month (backfill)")
    args = ap.parse_args()

    folders = sorted(p for p in ARCHIVE_ROOT.glob("[0-9][0-9][0-9][0-9]/[0-9][0-9]") if p.is_dir())
    if not (INDEX_DIR / "months.json").exists():
        args.all = True  # first run after deploy backfills the whole archive by itself
    if not args.all:
        folders = folders[-2:]  # current + previous folder covers LA/UTC month edges
    entries = scan(folders)

    by_month: dict[str, list] = {}
    for e in entries:
        by_month.setdefault(e["date_la"][:7], []).append(e)
    # A month at the edge of the scanned folders may be partial; only write months fully covered.
    if not args.all and folders:
        first_folder_month = "-".join(folders[0].parts[-2:])
        by_month = {m: v for m, v in by_month.items() if m >= first_folder_month}

    changed = 0
    for month, items in by_month.items():
        changed += write_if_changed(INDEX_DIR / f"{month}.json", {"month": month, "runs": items})

    # months.json: rebuild from all index files so it stays complete in incremental mode.
    months = []
    for f in sorted(INDEX_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json")):
        runs = json.loads(f.read_text(encoding="utf-8"))["runs"]
        days: dict[str, int] = {}
        for r in runs:
            days[r["date_la"]] = days.get(r["date_la"], 0) + 1
        months.append({"month": f.stem, "days": days})
    changed += write_if_changed(INDEX_DIR / "months.json", {"months": months})
    print(f"archive index: {len(entries)} runs scanned, {changed} file(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
