"""The summary's closing timestamp line, written by code instead of the model.

The model used to convert the UTC timestamps to Pacific time itself. It kept the
daylight-saving offset after DST ended (2026-11-01), so every summary showed the
wrong hour. Now the line is computed here with the IANA time zone database, which
picks PST or PDT for each moment, so DST changes are handled every run without
anyone touching the prompt. Any timestamp line the model writes anyway is removed
and replaced.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")

# Matches a model-written closing line (and anything after it in that paragraph),
# in the wording the old prompt asked for or close variants.
_MODEL_LINE_RE = re.compile(
    r"[ \t]*\bThis data summary was (?:last )?updated at\b[^\n]*(?:\n(?!\n)[^\n]*)*",
    flags=re.IGNORECASE,
)


def format_pacific(utc_iso: str | None) -> str:
    """'2026-11-01T19:36:00Z' -> 'November 1, 2026 at 11:36 AM PST'."""
    if not utc_iso:
        return "an unrecorded time"
    try:
        dt = datetime.fromisoformat(utc_iso.replace("Z", "+00:00")).astimezone(PACIFIC)
    except ValueError:
        return "an unrecorded time"
    hour = dt.strftime("%I").lstrip("0") or "12"
    return f"{dt.strftime('%B')} {dt.day}, {dt.year} at {hour}:{dt.strftime('%M %p')} {dt.tzname()}"


def closing_line(summary_json_text: str) -> str:
    """The standard closing line for a summary built from this summary JSON."""
    try:
        data = json.loads(summary_json_text)
    except ValueError:
        data = {}
    downloaded = data.get("downloaded_at")
    processed = (data.get("source_update_times") or {}).get("data_processed_at")
    return (
        f"This data summary was updated at {format_pacific(downloaded)} "
        f"and is based on data published by the City of Long Beach at {format_pacific(processed)}."
    )


def apply_closing_line(text: str, line: str) -> str:
    """Remove any timestamp line the model wrote and end the text with `line`."""
    body = _MODEL_LINE_RE.sub("", text).rstrip()
    return f"{body}\n\n{line}"
