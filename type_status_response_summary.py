"""
type_status_response_summary.py

Parses the most recent full export (timestamped) — supports both compressed (.json.gz)
and uncompressed (.json) formats — and computes:
- Per-type status totals
- Average response times
- Windowed summaries (All-time, 90d, 60d, 30d, 7d, 1d, 4h)

Writes CURRENT summary JSON to:
    data/summary_results_current.json

Also writes ARCHIVAL JSON to:
    data/archive/YYYY/MM/summary_json_<timestamp>.json

Logs all runs to:
    data/logs/parse_log_YYYY-MM-DD.txt
"""

import json
import os
import sys
import gzip
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import requests

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
    """Extract timestamp (UTC) from export filename pattern."""
    try:
        stem = Path(filename).stem.replace(".json", "").replace(".gz", "")
        ts_str = stem.split("_")[-1]
        return datetime.strptime(ts_str, "%Y-%m-%dT%H%MZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def find_latest_export_file(data_dir=DATA_DIR):
    """Find latest timestamped export (.json or .json.gz)."""
    files = list(Path(data_dir).glob("service_requests_full_*.json*"))
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
    """Parse ISO datetime safely."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def load_export_readonly(export_path):
    """Load JSON or GZipped JSON export file."""
    if str(export_path).endswith(".gz"):
        with gzip.open(export_path, "rt", encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        with open(export_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


# ------------------------------
# Metadata fetch
# ------------------------------

def fetch_source_update_timestamps(verbose=True):
    """
    Fetch dataset metadata from Opendatasoft (supports Make.com wrapper).
    Extracts data_processed, metadata_processed, modified timestamps.
    """

    url = "https://longbeach.opendatasoft.com/api/explore/v2.1/catalog/datasets/service-requests"

    output = {
        "data_processed_at": None,
        "metadata_processed_at": None,
        "modified_at": None
    }

    if verbose:
        print("\n==========================================")
        print("🔎 Fetching dataset metadata from Opendatasoft")
        print("==========================================")

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        payload = resp.json()

        # Format detection
        if isinstance(payload, list) and len(payload) > 0 and "data" in payload[0]:
            metadata_root = payload[0].get("data", {})
        elif isinstance(payload, dict) and "metas" in payload:
            metadata_root = payload
        elif isinstance(payload, dict) and "data" in payload and "metas" in payload["data"]:
            metadata_root = payload["data"]
        else:
            metadata_root = {}

        default_meta = {}
        if "metas" in metadata_root and "default" in metadata_root["metas"]:
            default_meta = metadata_root["metas"]["default"]

        dp = default_meta.get("data_processed")
        mp = default_meta.get("metadata_processed")
        md = default_meta.get("modified")

        for key, raw in [
            ("data_processed_at", dp),
            ("metadata_processed_at", mp),
            ("modified_at", md)
        ]:
            if raw:
                dt = parse_datetime_iso(raw)
                if dt:
                    output[key] = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    except Exception as e:
        log_event(f"WARNING: Could not fetch source timestamps: {e}")

    return output


# ------------------------------
# Core Aggregation
# ------------------------------

def summarize_by_type(records):
    """Aggregate counts & average response times per type."""
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
    """Print human-readable summary."""
    print(f"\n=== {label} ===")
    if not summary_by_type:
        print("No records found.")
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
    """Write JSON safely via temp-file atomic swap."""
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

def main() -> int:
    """Returns 0 on success, non-zero exit code on failure (Phase 1.4)."""
    start_time = datetime.now(timezone.utc)
    log_event("Starting summary generation.")

    try:
        latest_file, export_ts = find_latest_export_file(DATA_DIR)
    except Exception as e:
        print(f"FATAL locating export: {e}", file=sys.stderr)
        log_event(f"FATAL locating export: {e}")
        return 2

    print(f"Using latest export: {latest_file.name} (timestamp: {export_ts.isoformat()})")

    try:
        records = load_export_readonly(latest_file)
    except Exception as e:
        print(f"FATAL loading export: {e}", file=sys.stderr)
        log_event(f"FATAL loading export: {e}")
        return 3

    now = datetime.now(timezone.utc)

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
                }
                for t, s in agg.items()
            }
        }

        log_event(f"{label}: {len(subset)} records summarized.")

    # Metadata timestamps
    source_ts = fetch_source_update_timestamps(verbose=True)

    summary_data["source_update_times"] = {
        "data_processed_at": source_ts.get("data_processed_at"),
        "metadata_processed_at": source_ts.get("metadata_processed_at"),
        "modified_at": source_ts.get("modified_at")
    }

    summary_data["downloaded_at"] = export_ts.strftime("%Y-%m-%dT%H:%M:%SZ")

    #
    # ***************  WRITE CURRENT JSON SUMMARY  ***************
    #
    summary_path = f"{DATA_DIR}/summary_results_current.json"

    try:
        write_json_atomically(summary_data, summary_path)
        print(f"Wrote CURRENT JSON summary atomically to: {summary_path}")
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        log_event(f"SUCCESS: Current summary written to {summary_path}. Duration: {duration:.1f}s")
    except Exception as e:
        print(f"FATAL writing JSON summary: {e}", file=sys.stderr)
        log_event(f"FATAL writing summary: {e}")
        return 4

    #
    # ***************  WRITE ARCHIVE COPY (YEAR/MONTH)  ***************
    #

    now_local = datetime.now()
    year = now_local.strftime("%Y")
    month = now_local.strftime("%m")
    timestamp_local = now_local.strftime("%Y-%m-%d_%H-%M-%S")

    archive_dir = Path(f"data/archive/{year}/{month}")
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_json_path = archive_dir / f"summary_json_{timestamp_local}.json"

    try:
        with open(archive_json_path, "w", encoding="utf-8") as af:
            json.dump(summary_data, af, indent=2, ensure_ascii=False)
        print(f"📦 Archived summary written → {archive_json_path}")
        log_event(f"Archived summary JSON written to {archive_json_path}")
    except Exception as e:
        # Archive write is best-effort: warn but do not fail the run.
        print(f"WARNING: Failed to write JSON archive copy: {e}", file=sys.stderr)
        log_event(f"WARNING: Could not archive JSON summary: {e}")

    return 0


# --------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())
