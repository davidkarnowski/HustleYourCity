# Triggers Make.com Web Hooks using GitHub secret variables for the URL and API Keys

import os
import json
import requests
from datetime import datetime, timezone
import time
import sys

def trigger_make_webhook(url: str, api_key: str, wait_seconds: int = 180, label: str = "default"):
    """Trigger a Make.com webhook and wait for scenario to finish.

    Args:
        url (str): The Make.com webhook URL
        api_key (str): Make.com API key (x-make-apikey)
        wait_seconds (int): Buffer wait time after trigger
        label (str): logging label
    """
    trigger_time = datetime.now(timezone.utc).isoformat()

    payload = {
        "event": f"github_trigger_{label}",
        "repository": os.getenv("GITHUB_REPOSITORY", "unknown_repo"),
        "trigger_time": trigger_time,
        "source": "github_actions",
    }

    print(f"[INFO] Triggering Make.com webhook ({label}) at {trigger_time}")
    print(f"[INFO] Payload: {json.dumps(payload)}")

    headers = {
        "Content-Type": "application/json",
        "x-make-apikey": api_key,
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"[INFO] Webhook HTTP status: {response.status_code}")

        if response.status_code not in (200, 202):
            print("[ERROR] Webhook did not return success")
            print("Response text:", response.text)
            sys.exit(1)

    except Exception as e:
        print("[ERROR] Webhook trigger failed:", str(e))
        sys.exit(1)

    print(f"[INFO] Waiting {wait_seconds} seconds for Make.com flow + GitHub Pages update...")
    time.sleep(wait_seconds)
    print("[INFO] Continuing pipeline.")

if __name__ == "__main__":
    # CLI args fallback — protects future reusability
    url = os.getenv("MAKE_WEBHOOK_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
    api_key = os.getenv("MAKE_WEBHOOK_KEY") or (sys.argv[2] if len(sys.argv) > 2 else None)

    if not url or not api_key:
        print("[FATAL] Missing webhook URL or API key.")
        sys.exit(1)

    trigger_make_webhook(url, api_key, wait_seconds=int(os.getenv("WAIT_SECONDS", "180")), label="llm_summaries")
