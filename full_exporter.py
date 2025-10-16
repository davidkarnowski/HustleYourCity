"""
full_exporter.py

Downloads the full City of Long Beach service request dataset via Opendatasoft's
'exports' endpoint in JSON format and saves it to a timestamped file.

This version is optimized for general cloud or local runtimes:
- Uses chunked streaming download to handle large datasets safely
- Adds visible progress logging for long downloads
- Includes explicit timeout and retry handling
- Stores files under ./data and ./data/logs
- Adds gzip compression to stay under GitHub’s 100 MB file size limit
"""

import requests
import json
import os
import gzip
import time
from datetime import datetime, timezone
from config import BASE_URL, DATASET_ID
from pathlib import Path


# === Local Data and Logging Setup =============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Root of the current project
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(DATA_DIR, "logs")

# Ensure directories exist
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)


def log_event(message: str):
    """Append timestamped event messages to a daily export log."""
    log_file = os.path.join(LOG_DIR, f"export_log_{datetime.now().strftime('%Y-%m-%d')}.txt")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write(f"[{timestamp}] {message}\n")


def download_full_export_json(max_retries: int = 3):
    """
    Downloads the full dataset and saves it to a timestamped JSON file.
    Uses chunked streaming with progress logging to handle large files.
    Then compresses it to a .json.gz file to reduce file size for GitHub storage.
    Returns the output path (compressed) and record count.
    """

    start_time = datetime.now(timezone.utc)
    log_event("Starting full dataset export.")
    print("Attempting full dataset export (JSON format)...")

    export_url = f"{BASE_URL.rstrip('/')}/catalog/datasets/{DATASET_ID}/exports/json"
    print(f"Requesting data from: {export_url}\n")

    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    raw_output_file = os.path.join(DATA_DIR, f"service_requests_full_{timestamp_str}.json")
    compressed_output_file = raw_output_file + ".gz"

    # === Attempt with retries ==================================================
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}/{max_retries} - Connecting...")
            response = requests.get(export_url, stream=True, timeout=(10, 600))
            response.raise_for_status()

            print("Connection established. Downloading in chunks...")
            chunk_size = 1024 * 1024  # 1 MB
            total_downloaded = 0

            with open(raw_output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        total_downloaded += len(chunk)
                        # Print progress every 10 MB
                        if total_downloaded % (10 * chunk_size) < chunk_size:
                            print(f"  Downloaded {total_downloaded / (1024 * 1024):.1f} MB...")

            print(f"Download complete. Saved raw file to: {raw_output_file}")
            break

        except requests.exceptions.Timeout:
            print(f"Attempt {attempt} timed out after 10 minutes, retrying...")
            log_event(f"Timeout on attempt {attempt}")
            time.sleep(5)
        except requests.exceptions.RequestException as e:
            print(f"Request failed on attempt {attempt}: {e}")
            log_event(f"RequestException on attempt {attempt}: {e}")
            time.sleep(5)
    else:
        print("All attempts failed. Exiting.")
        log_event("All retries failed.")
        return None, 0

    # === Validate JSON =========================================================
    try:
        with open(raw_output_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("Error: Response is not valid JSON.")
        log_event("ERROR: Response not valid JSON.")
        return raw_output_file, 0

    # Handle both array and dict-style responses
    if isinstance(data, dict) and "results" in data:
        count = len(data["results"])
    elif isinstance(data, list):
        count = len(data)
    else:
        count = 0

    # === Compress File =========================================================
    print(f"Compressing {raw_output_file} to {compressed_output_file} ...")
    try:
        with open(raw_output_file, "rb") as fin, gzip.open(compressed_output_file, "wb") as fout:
            fout.writelines(fin)
        compressed_size = os.path.getsize(compressed_output_file) / (1024 * 1024)
        print(f"Compression complete. Compressed size: {compressed_size:.2f} MB")

        # Optionally remove uncompressed file to save space
        os.remove(raw_output_file)
        print(f"Removed uncompressed file: {raw_output_file}")

    except Exception as e:
        print(f"Error during compression: {e}")
        log_event(f"ERROR during compression: {e}")
        return raw_output_file, count

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()

    print(f"\nSaved compressed dataset to: {compressed_output_file}")
    print(f"Approx. record count: {count}")
    print(f"Duration: {duration:.1f} seconds\n")

    log_event(
        f"Export complete. File: {compressed_output_file}, Records: {count}, "
        f"Compressed Size: {compressed_size:.2f} MB, Duration: {duration:.1f}s"
    )

    return compressed_output_file, count


# === Main Execution ============================================================
if __name__ == "__main__":
    path, total_records = download_full_export_json()
    if total_records == 0:
        print("No records found or dataset too large for JSON export.")
        log_event("No records found or dataset too large.")
    else:
        print(f"Successfully downloaded {total_records} records to {path}.")
        log_event(f"SUCCESS: {total_records} records exported to {path}.")
