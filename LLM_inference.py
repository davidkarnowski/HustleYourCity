# ==========================================================
# Hustle Long Beach — Gemini 3.1 Flash-Lite Preview LLM Inference Module
# (Dynamic model selection + verbose output + retry logic)
# ==========================================================
# Generates natural-language summaries for civic-data dashboards.
# Uses Google's Gemini 3.1 Flash-Lite Preview (or alternate models) via the
# AI Studio API. Reads API key from environment variable:
#
#   GOOGLE_AI_STUDIO_API_KEY
#
# Author: Hustle Long Beach project
# ==========================================================

import os
import json
import requests
import time
from pathlib import Path
from datetime import datetime

# ==========================================================
# Configuration
# ==========================================================

# Base URL for all Gemini model variants
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Default model — can be changed dynamically at runtime
DEFAULT_MODEL = "gemini-3.1-flash-lite-preview"

# ==========================================================
# Base system prompt — defines tone, language, and constraints
# ==========================================================
HUSTLE_BASE_PROMPT = """
You are a third-party government accountability JSON interpreter for the Hustle Long Beach! community that evaluates city service response times. You are not officially part of the City of Long Beach government and you do not represent any agency management so do not refer to the work as ours or done by "we". You are ready to make sense of city service data from the Long Beach service call data via JSON. Evaluate the data and write a short social media update about the latest data update. We don't need all the data to be revealed and the post created should be short enough for a social media post. Make the data interpretable for the citizens of Long Beach. Hour counts over 72-hours should be expressed in days, weeks or months. Hour counts below 90 minutes should be measured in minutes. Unusually low responses may be due to administrative closures and not actual work completions. Remember that you are just trying to make sure the public knows about the latest response times, call totals and changes. Use facts and statistics to back up your post's language, always being factual about your response. Encourage followers to use the Go Long Beach service application to report issues to the city. Use straight-forward and simple language, nothing elaborate or flowery. 

When writing the social media post, use only plain text that conforms to LinkedIn's Little Text Format:
- Do not include any emojis or non-ASCII characters.
- Use only straight quotes (" ") and apostrophes ('), and standard hyphens (-).
- Replace all non-breaking spaces with normal spaces.
- Do not include markdown, HTML, or Unicode styling.
- Separate paragraphs with a single blank line.
- Output only the final post text, no metadata, no labels, and no code block formatting.

Your last lines should always include the date-time stamps of the JSON "downloaded_at" and the "data_processed_at" fields. The data_processed_at field is the time in which the city last updated the actual data. This should be described to users as the time frame end for the data summary. Including the downloaded_at data will let users know when this summary was produced. Because these values will be zulu(utc), convert it to current Los Angeles time (PST/PDT). Use the format "This data summary was updated at <insert \"downloaded_at\" value> and is based on data published by the City of Long Beach at <insert \"data_processed_at\" value>
""".strip()

# ==========================================================
# Time-frame prompts — adds period-specific focus
# ==========================================================
TIMEFRAME_PROMPTS = {
    "4hours": """
This summary will focus on significant data changes only in the past 4-hours and any case type and averages during that time frame that have significantly low or high response times. If the dataset is small, state that no major changes are available yet. Use the data under "Last 4 Hours".
""",
    "24hours": """
This summary will focus on significant data changes only in the past 24-hours and any case type and averages during that time frame that have significantly low or high response times. Use the data under "Last 1 Days".
""",
    "7days": """
This summary will focus on significant data changes only in the past 7 days. Use the data under "Last 7 Days".
""",
    "30days": """
This summary will focus on significant data changes only in the past 30 days. Use the data under "Last 30 Days".
""",
    "90days": """
This summary will focus on significant data changes only in the past 90 days. Use the data under "Last 90 Days".
""",
}

# ==========================================================
# Helper: Resilient API call with exponential backoff
# ==========================================================
def post_with_retries(url, headers, payload, max_retries=5, backoff_factor=2):
    """
    Sends POST request with exponential backoff on transient errors.
    Retries on: 429 (rate limit), 500, 503, and network timeouts.
    """
    for attempt in range(1, max_retries + 1):
        try:
            print(f"📡 Attempt {attempt}/{max_retries} — contacting Gemini API...")
            res = requests.post(url, headers=headers, json=payload, timeout=90)

            # Retry if the model is overloaded or rate limited
            if res.status_code in (429, 500, 503):
                wait = backoff_factor ** attempt
                print(f"⚠️ Received {res.status_code}: {res.reason}. Waiting {wait}s before retry...")
                time.sleep(wait)
                continue

            # Other non-successful codes
            if res.status_code != 200:
                raise RuntimeError(f"Gemini API error {res.status_code}: {res.text}")

            print("✅ Successful response received from Gemini API.")
            return res

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            wait = backoff_factor ** attempt
            print(f"⚠️ Network issue: {e}. Retrying in {wait}s...")
            time.sleep(wait)

    # If all retries failed, abort with a clear message
    raise RuntimeError("❌ Gemini API failed after multiple retry attempts.")


# ==========================================================
# Core LLM inference function
# ==========================================================
def run_gemini_inference(
    system_prompt: str,
    timeframe_prompt: str,
    user_prompt: str,
    output_file: str = None,
    model: str = DEFAULT_MODEL
) -> str:
    """
    Combines base + timeframe prompts, sends them with JSON data
    to Gemini, and writes the resulting summary to a text file.
    """

    # Combine all textual instructions for the model
    final_prompt = (
        system_prompt.strip()
        + "\n\n"
        + timeframe_prompt.strip()
        + "\n\nYou will now receive the JSON data."
    )

    # Display start info for this inference cycle
    print("------------------------------------------------------")
    print(f"[{datetime.now()}] Starting inference with model: {model}")
    print("------------------------------------------------------")

    # Retrieve API key from environment
    api_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing environment variable: GOOGLE_AI_STUDIO_API_KEY")

    # Build request headers for authentication
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    # Construct the full model endpoint dynamically
    url = f"{GEMINI_API_BASE}/{model}:generateContent"
    print(f"📍 Using endpoint: {url}")

    # Assemble the request body according to Gemini schema
    payload = {
        "contents": [
            {"parts": [
                {"text": final_prompt},
                {"text": user_prompt.strip()}
            ]}
        ],
        "generationConfig": {
            "temperature": 0.3,        # Low temperature for factual output
            "maxOutputTokens": 4096    # Reasonable max token limit
        }
    }

    # Perform the API call using retry helper
    res = post_with_retries(url, headers, payload)
    data = res.json()

    # Attempt to extract text from the returned JSON
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        print("⚠️ Unexpected response format:")
        print(json.dumps(data, indent=2))
        raise RuntimeError("Gemini API returned unrecognized structure.")

    # Display a preview of generated content
    preview = text[:250].replace("\n", " ")
    print(f"📝 Preview: {preview}...")

    # Write output to file if path provided
    if output_file:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"💾 Saved output to {output_file}")

        # ==============================================================
        # ARCHIVE SYSTEM (timestamped history of all summaries)
        # ==============================================================
        now = datetime.now()

        year = now.strftime("%Y")
        month = now.strftime("%m")
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

        # Create: data/archive/YYYY/MM/
        archive_dir = Path(f"data/archive/{year}/{month}")
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Derive a readable timeframe label from filename
        tf_label = (
            Path(output_file)
            .stem
            .replace("current_", "")
            .replace("_text_status", "")
        )

        archive_file = archive_dir / f"summary_{tf_label}_{timestamp}.txt"

        # Write archive copy
        with open(archive_file, "w", encoding="utf-8") as af:
            af.write(text)

        print(f"📦 Archived summary written → {archive_file}")
        # ==============================================================

    print(f"[{datetime.now()}] ✅ Completed inference for {output_file}")
    print("------------------------------------------------------\n")
    return text


# ==========================================================
# Main execution — Generate all timeframe summaries
# ==========================================================
if __name__ == "__main__":
    print("======================================================")
    print("🚀 Hustle Long Beach — Gemini 3.1 Flash-Lite Preview Inference Started")
    print("======================================================")

    # Load current dataset
    data_path = Path("data/summary_results_current.json")
    if not data_path.exists():
        raise FileNotFoundError("❌ Missing data/summary_results_current.json")

    with open(data_path, "r", encoding="utf-8") as f:
        json_payload = f.read()

    print(f"✅ Loaded JSON ({len(json_payload)} chars)\n")

    # Map each timeframe to its corresponding output file
    output_map = {
        "4hours":  "data/current_4_hour_text_status.txt",
        "24hours": "data/current_24_hour_text_status.txt",
        "7days":   "data/current_7_day_text_status.txt",
        "30days":  "data/current_30_day_text_status.txt",
        "90days":  "data/current_90_day_text_status.txt",
    }

    # Iterate through each timeframe and generate summaries
    for timeframe, prompt in TIMEFRAME_PROMPTS.items():
        outfile = output_map[timeframe]
        print(f"▶️ Generating summary for: {timeframe}")
        text = run_gemini_inference(
            HUSTLE_BASE_PROMPT,
            prompt,
            json_payload,
            output_file=outfile,
            model=DEFAULT_MODEL  # Dynamically referenced
        )
        print(f"✅ Summary complete for {timeframe}\n")

    print("======================================================")
    print("🎉 All summaries generated successfully!")
    print("======================================================")
