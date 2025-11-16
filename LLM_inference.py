# ==========================================================
# Hustle Long Beach — Cerebras LLM Inference Module (Resilient v2)
# Adds exponential backoff and fallback file creation if service unavailable
# ==========================================================

import os
import json
import time
import requests
from pathlib import Path

# ==========================================================
# API configuration
# ==========================================================
CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
DEFAULT_MODEL = "gpt-oss-120b"
MAX_RETRIES = 10            # total attempts including first
INITIAL_DELAY = 30         # seconds before first retry
FALLBACK_MESSAGE = (
    "Automated data summaries are temporarily unavailable.\n"
    "The Hustle Long Beach dashboard will update once the LLM service is back online.\n"
    "All table data and metrics have still been refreshed successfully.\n"
    "Please check back soon for a new update."
)

# ==========================================================
# Base system prompt
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
# Time-frame addenda
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
# LLM inference function with exponential retry + fallback
# ==========================================================
def run_cerebras_inference(
    system_prompt: str,
    timeframe_prompt: str,
    user_prompt: str,
    output_file: str,
    model: str = DEFAULT_MODEL
) -> str:
    final_prompt = (
        system_prompt.strip()
        + "\n\n"
        + timeframe_prompt.strip()
        + "\n\nYou will now receive the JSON data."
    )

    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("❌ Missing environment variable: CEREBRAS_API_KEY")
        _write_fallback(output_file)
        return FALLBACK_MESSAGE

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": final_prompt},
            {"role": "user", "content": user_prompt.strip()},
        ],
        "temperature": 0.3,
        "max_tokens": 1600,
        "stream": False,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    attempt = 0
    delay = INITIAL_DELAY

    while attempt < MAX_RETRIES:
        attempt += 1
        print("\n------------------------------------------------------")
        print(f"[Attempt {attempt}/{MAX_RETRIES}] Contacting Cerebras API...")

        try:
            res = requests.post(CEREBRAS_API_URL, headers=headers, json=payload, timeout=60)
            print(f"Response code: {res.status_code}")

            if res.status_code == 200:
                text = res.json()["choices"][0]["message"]["content"].strip()
                Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w") as f:
                    f.write(text)
                print(f"✅ Successful response received and saved to {output_file}")
                return text
            else:
                print(f"⚠️ Cerebras returned error {res.status_code}: {res.text}")

        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")

        if attempt < MAX_RETRIES:
            print(f"⏳ Waiting {delay} seconds before retry...")
            time.sleep(delay)
            delay *= 2  # exponential backoff

    # All retries exhausted
    print("❌ Cerebras service unavailable after multiple attempts. Writing fallback text file.")
    _write_fallback(output_file)
    return FALLBACK_MESSAGE


# ==========================================================
# Helper: write fallback file
# ==========================================================
def _write_fallback(output_file: str):
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        f.write(FALLBACK_MESSAGE)
    print(f"⚙️  Fallback file written: {output_file}")


# ==========================================================
# Main — generate all 5 period summaries
# ==========================================================
if __name__ == "__main__":
    data_path = Path("data/summary_results_current.json")
    if not data_path.exists():
        print("❌ Missing data/summary_results_current.json — cannot proceed.")
        exit(0)

    with open(data_path, "r") as f:
        json_payload = f.read()

    output_map = {
        "4hours":  "data/current_4_hour_text_status.txt",
        "24hours": "data/current_24_hour_text_status.txt",
        "7days":   "data/current_7_day_text_status.txt",
        "30days":  "data/current_30_day_text_status.txt",
        "90days":  "data/current_90_day_text_status.txt",
    }

    for timeframe, prompt in TIMEFRAME_PROMPTS.items():
        outfile = output_map[timeframe]
        print("\n======================================================")
        print(f"🚀 Generating {timeframe} summary → {outfile}")
        print("======================================================")

        text = run_cerebras_inference(
            HUSTLE_BASE_PROMPT,
            prompt,
            json_payload,
            output_file=outfile
        )
        print(f"✅ Output ready for {timeframe} → {outfile}")

    print("\n🏁 Completed all inference tasks — continuing dashboard build.")
