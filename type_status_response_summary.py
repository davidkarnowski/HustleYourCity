"""
type_status_response_summary_safe.py

Parses the most recent full export (timestamped) and computes:
- Per-type status totals
- Average response times
- Windowed summaries (All-time, 90d, 60d, 30d, 7d, 1d, 4h)

Writes summary JSON named after the same timestamp as the export file, e.g.:
    data/summary_stats_2025-10-16T1200Z.json

Logs all runs to:
    data/logs/parse_log_YYYY-MM-DD.txt
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter

DATA_DIR = "data"
LOG_DIR = "data/logs"


# ------------------------------
# Logging
# ------------------------------

def log_event(message: str):
    """Append timestamped log message to daily parse log."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"parse_log_{datetime.now().strftime('%Y-%m-%d')}.txt")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write(f"[{timestamp}] {message}\n")


# ------------------------------
# Helper: Locate export and timestamp
# ------------------------------

def extract_timestamp_from_filename(filename):
    try:
        stem = Path(filename).stem
        ts_str = stem.split("_")[-1]
        return datetime.strptime(ts_str, "%Y-%m-%dT%H%MZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def find_latest_export_file(data_dir=DATA_DIR):
    files = list(Path(data_dir).glob("service_requests_full_*.json"))
    if not files:
        raise FileNotFoundError(f"No export files found in {data_dir}")

    dated_files = []
    for f in files:
        ts = extract_timestamp_from_filename(f.name)
        if ts:
            dated_files.append((ts, f))

    if not dated_files:
        raise FileNotFoundError("No timestamped export files found.")

    latest_ts, latest_file = max(dated_files, key=lambda x: x[0])
    return latest_file, latest_ts


# ------------------------------
# Parsing Helpers
# ------------------------------

def parse_datetime_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def load_export_readonly(export_path):
    with open(export_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data["results"] if isinstance(data, dict) and "results" in data else data


# ------------------------------
# Core Aggregation
# ------------------------------

def summarize_by_type(records):
    agg = defaultdict(lambda: {
        "total": 0,
        "status_counts": Counter(),
        "response_times_hours": []
    })

    for rec in records:
        t = rec.get("type") or "Unknown"
        s = rec.get("status") or "Unknown"
        agg[t]["total"] += 1
        agg[t]["status_counts"][s] += 1

        created = parse_datetime_iso(rec.get("createddate"))
        closed = parse_datetime_iso(rec.get("closeddate"))
        if created and closed and closed > created:
            delta = (closed - created).total_seconds() / 3600.0
            if delta >= 0:
                agg[t]["response_times_hours"].append(delta)

    for t, stats in agg.items():
        times = stats["response_times_hours"]
        stats["avg_response_hours"] = (sum(times) / len(times)) if times else None

    return agg


def print_type_table(label, summary_by_type):
    print(f"\n=== {label} ===")
    if not summary_by_type:
        print("No records found in this window.")
        return

    header = f"{'Service Type':30} {'Total':>8} {'Closed':>8} {'In Progress':>12} {'New':>8} {'Avg Response (hrs)':>20}"
    print(header)
    print("-" * len(header))

    for type_name, stats in sorted(summary_by_type.items(), key=lambda x: x[1]["total"], reverse=True):
        total = stats["total"]
        closed = stats["status_counts"].get("Closed", 0)
        in_prog = stats["status_counts"].get("In Progress", 0)
        new = stats["status_counts"].get("New", 0)
        avg = stats["avg_response_hours"]
        avg_str = f"{avg:8.2f}" if avg else "       —"
        print(f"{type_name:30} {total:8d} {closed:8d} {in_prog:12d} {new:8d} {avg_str:20s}")

    print("-" * len(header))


# ------------------------------
# Safe Write
# ------------------------------

def write_json_atomically(obj, dest_path):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="tmp_summary_", suffix=".json", dir=os.path.dirname(dest_path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(obj, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_path, dest_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# ------------------------------
# Main Routine
# ------------------------------

def main():
    start_time = datetime.now(timezone.utc)
    log_event("Starting summary generation.")

    try:
        latest_file, export_ts = find_latest_export_file(DATA_DIR)
    except Exception as e:
        print(f"Error: {e}")
        log_event(f"ERROR locating export: {e}")
        return

    print(f"Using latest export: {latest_file.name} (timestamp: {export_ts.isoformat()})")

    try:
        records = load_export_readonly(latest_file)
    except Exception as e:
        print(f"Error loading export: {e}")
        log_event(f"ERROR loading export: {e}")
        return

    now = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # Add the new "Last 4 Hours" window to the existing lineup
    # --------------------------------------------------------
    windows = [
        ("All-Time", records),
        ("Last 90 Days", [r for r in records if (d := parse_datetime_iso(r.get("createddate"))) and d >= now - timedelta(days=90)]),
        ("Last 60 Days", [r for r in records if (d := parse_datetime_iso(r.get("createddate"))) and d >= now - timedelta(days=60)]),
        ("Last 30 Days", [r for r in records if (d := parse_datetime_iso(r.get("createddate"))) and d >= now - timedelta(days=30)]),
        ("Last 7 Days",  [r for r in records if (d := parse_datetime_iso(r.get("createddate"))) and d >= now - timedelta(days=7)]),
        ("Last 1 Days",  [r for r in records if (d := parse_datetime_iso(r.get("createddate"))) and d >= now - timedelta(days=1)]),
        ("Last 4 Hours", [r for r in records if (d := parse_datetime_iso(r.get("createddate"))) and d >= now - timedelta(hours=4)]),
    ]

    summary_data = {}
    for label, subset in windows:
        agg = summarize_by_type(subset)
        print_type_table(label, agg)
        summary_data[label] = {
            "types": {
                t: {
                    "total": s["total"],
                    "status_counts": dict(s["status_counts"]),
                    "avg_response_hours": s["avg_response_hours"]
                } for t, s in agg.items()
            }
        }

        log_event(f"{label}: {len(subset)} records summarized.")

    summary_path = f"{DATA_DIR}/summary_stats_{export_ts.strftime('%Y-%m-%dT%H%MZ')}.json"

    try:
        write_json_atomically(summary_data, summary_path)
        print(f"Wrote JSON summary atomically to: {summary_path}")
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        log_event(f"SUCCESS: Summary written to {summary_path}. Duration: {duration:.1f}s")
    except Exception as e:
        print(f"Error writing JSON summary: {e}")
        log_event(f"ERROR writing summary: {e}")


if __name__ == "__main__":
    main()
