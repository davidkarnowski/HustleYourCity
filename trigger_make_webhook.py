# -----------------------------------------------------------------------
# Trigger a Make.com webhook using GitHub Actions environment variables.
# -----------------------------------------------------------------------


import os
import json
import requests
from datetime import datetime, timezone
import sys

def trigger_make_webhook(url: str, api_key: str, label: str = "default"):
    # Get current UTC ISO timestamp for metadata logging and Make payload
    trigger_time = datetime.now(timezone.utc).isoformat()

    # Build JSON payload
    payload = {
        "event": f"github_trigger_{label}",
        "repository": os.getenv("GITHUB_REPOSITORY", "unknown_repo"),
        "trigger_time": trigger_time,
        "source": "github_actions",
    }

    print(f"[INFO] Triggering Make.com webhook ({label}) at {trigger_time}")
    print(f"[INFO] Payload: {json.dumps(payload)}")

    # Headers including Make API key
    headers = {
        "Content-Type": "application/json",
        "x-make-apikey": api_key,
    }

    try:
        # POST request to Make.com scenario webhook
        response = requests.post(url, headers=headers, json=payload)
        print(f"[INFO] Webhook HTTP status: {response.status_code}")

        # Acceptable success responses
        if response.status_code not in (200, 202):
            print("[ERROR] Make.com webhook returned a non-success status")
            print("Response text:", response.text)
            sys.exit(1)

    except Exception as e:
        print("[ERROR] Exception while calling Make.com webhook:", str(e))
        sys.exit(1)

    print("[INFO] Webhook trigger completed successfully")

# -----------------------------------------------------------------------
# Main execution path: expect URL + KEY from environment variables
# -----------------------------------------------------------------------
if __name__ == "__main__":
    # Read secrets from environment variables
    url = os.getenv("MAKE_WEBHOOK_URL")
    api_key = os.getenv("MAKE_WEBHOOK_KEY")

    # Validate environment variables
    if not url or not api_key:
        print("[FATAL] Missing MAKE_WEBHOOK_URL or MAKE_WEBHOOK_KEY environment variables")
        sys.exit(1)

    # Call the webhook trigger function
    trigger_make_webhook(url, api_key, label="llm_summaries")
