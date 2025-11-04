# ==========================================================
# Hustle Long Beach — Cerebras LLM Inference Module
# Generates natural-language summaries for civic-data dashboard
# ==========================================================

import os
import json
import requests
from pathlib import Path


# ==========================================================
# API configuration
# ==========================================================
CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"
DEFAULT_MODEL = "gpt-oss-120b"


# ==========================================================
# Base system prompt
# ==========================================================
HUSTLE_BASE_PROMPT = """
You are a third-party government accountability JSON interpreter for the HustleLongBeach community that evaluates city service response times. You are not officially part of the City of Long Beach government and you do not represent any agency management so do not refer to the work as ours or done by "we". You are ready to make sense of city service data from the Long Beach service call data via JSON. Evaluate the data and write a short social media update about the latest data update. We don't need all the data to be revealed and the post created should be short enough for a social media post. Make the data interpretable for the citizens of Long Beach. Hour counts over 72-hours should be expressed in days, weeks or months. Hour counts below 90 minutes should be measured in minutes. Unusually low responses may be due to administrative closures and not actual work completions. Remember that you are just trying to make sure the public knows about the latest response times, call totals and changes. Use facts and statistics to back up your post's language, always being factual about your response. Encourage followers to use the Go Long Beach service application to report issues to the city. Use straight-forward and simple language, nothing elaborate or flowery. 

When writing the social media post, use only plain text that conforms to LinkedIn's Little Text Format:
- Do not include any emojis or non-ASCII characters.
- Use only straight quotes (" ") and apostrophes ('), and standard hyphens (-).
- Replace all non-breaking spaces with normal spaces.
- Do not include markdown, HTML, or Unicode styling.
- Separate paragraphs with a single blank line.
- Output only the final post text, no metadata, no labels, and no code block formatting.

Your very last line should always include the date-time stamp of the JSON "downloaded_at" field. This will let users know when this summary was produced. Because this value will be zulu(utc), convert it to current Los Angeles time (PST/PDT). Use the format "This data summary was updated at <insert \"downloaded_at\" value>."
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
# LLM inference function with output file option
# ==========================================================
def run_cerebras_inference(
    system_prompt: str,
    timeframe_prompt: str,
    user_prompt: str,
    output_file: str = None,
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
        raise RuntimeError("Missing environment variable: CEREBRAS_API_KEY")

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

    res = requests.post(CEREBRAS_API_URL, headers=headers, json=payload, timeout=60)
    if res.status_code != 200:
        raise RuntimeError(f"Cerebras error {res.status_code}: {res.text}")

    text = res.json()["choices"][0]["message"]["content"].strip()

    if output_file:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            f.write(text)

    return text


# ==========================================================
# Main — generate all 5 period summaries
# ==========================================================
if __name__ == "__main__":
    data_path = Path("data/summary_results_current.json")
    if not data_path.exists():
        raise FileNotFoundError("Missing data/summary_results_current.json")

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

        print(f"Generating {timeframe} → {outfile}")
        text = run_cerebras_inference(
            HUSTLE_BASE_PROMPT,
            prompt,
            json_payload,
            output_file=outfile
        )
        print(f"✅ Saved: {outfile}")
