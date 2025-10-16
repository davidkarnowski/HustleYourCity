"""
full_exporter.py

Downloads the full City of Long Beach service request dataset via Opendatasoft's
'exports' endpoint in JSON format and saves it to a timestamped file.

Also logs each export attempt and outcome to data/logs/export_log_YYYY-MM-DD.txt
"""

import requests
import json
import os
from datetime import datetime, timezone
from config import BASE_URL, DATASET_ID

LOG_DIR = "data/logs"


def log_event(message: str):
    """Append timestamped event messages to a daily export log."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"export_log_{datetime.now().strftime('%Y-%m-%d')}.txt")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write(f"[{timestamp}] {message}\n")


def download_full_export_json():
    """
    Downloads the full dataset and saves it to a timestamped JSON file.
    Returns the output path and record count.
    """

    start_time = datetime.now(timezone.utc)
    log_event("Starting full dataset export.")

    print("Attempting full dataset export (JSON format)...")

    export_url = f"{BASE_URL.rstrip('/')}/catalog/datasets/{DATASET_ID}/exports/json"
    print(f"Requesting data from: {export_url}")

    try:
        response = requests.get(export_url, timeout=600)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching dataset: {e}")
        log_event(f"ERROR during fetch: {e}")
        return None, 0

    try:
        data = response.json()
    except json.JSONDecodeError:
        print("Error: Response is not valid JSON.")
        log_event("ERROR: Response not valid JSON.")
        return None, 0

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    os.makedirs("data", exist_ok=True)
    output_file = f"data/service_requests_full_{timestamp}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if isinstance(data, dict) and "results" in data:
        count = len(data["results"])
    elif isinstance(data, list):
        count = len(data)
    else:
        count = 0

    file_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"\nSaved dataset to: {output_file}")
    print(f"File size: {file_size:.2f} MB")
    print(f"Approx. record count: {count}\n")

    log_event(f"Export complete. File: {output_file}, Records: {count}, Size: {file_size:.2f} MB, Duration: {(datetime.now(timezone.utc) - start_time).total_seconds():.1f}s")

    return output_file, count


if __name__ == "__main__":
    path, total_records = download_full_export_json()
    if total_records == 0:
        print("No records found or dataset too large for JSON export.")
        log_event("No records found or dataset too large.")
    else:
        print(f"Successfully downloaded {total_records} records to {path}.")
        log_event(f"SUCCESS: {total_records} records exported to {path}.")
