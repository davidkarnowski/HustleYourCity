"""LLM cascade orchestrator: try primary → secondary → archive fallback.

Default chain (per Eval doc Decision Log D-05, 2026-04-30):
    Gemini (primary)  →  OpenAI (secondary)  →  Archive (always-succeeds floor)

The OpenAI secondary is the user-confirmed mitigation for Gemini
preview-tier 503-overload events observed on 2026-04-30. See Plan 02
Task 2.4 Analysis section in /Users/dk/Projects/Hustle_Long_Beach/Plans/.

Environment variables consumed (all optional; defaults match production):
    LLM_PRIMARY              "gemini" (only supported value today)
    LLM_PRIMARY_MODEL        "gemini-3.1-flash-lite-preview"
    LLM_SECONDARY            "openai" (or "anthropic", or "" to disable)
    LLM_SECONDARY_MODEL      "gpt-4o-mini" (or per-provider default)
    GOOGLE_AI_STUDIO_API_KEY (required for Gemini)
    OPENAI_API_KEY           (required if LLM_SECONDARY=openai)
    ANTHROPIC_API_KEY        (required if LLM_SECONDARY=anthropic)
"""
import os
from pathlib import Path
from .prompts import HUSTLE_BASE_PROMPT, TIMEFRAME_PROMPTS
from .providers.base import GenerationRequest, ProviderError, Provider
from .providers.gemini import GeminiProvider
from .providers.archive import ArchiveProvider
from .validators import validate_output, ValidationError

OUTPUT_MAP = {
    "4hours":  Path("data/current_4_hour_text_status.txt"),
    "24hours": Path("data/current_24_hour_text_status.txt"),
    "7days":   Path("data/current_7_day_text_status.txt"),
    "30days":  Path("data/current_30_day_text_status.txt"),
    "90days":  Path("data/current_90_day_text_status.txt"),
}

# Mirrors the archival label convention used historically by LLM_inference.py.
ARCHIVE_LABEL = {
    "4hours":  "4_hour",
    "24hours": "24_hour",
    "7days":   "7_day",
    "30days":  "30_day",
    "90days":  "90_day",
}


def get_providers() -> list[Provider]:
    """Return the cascade in order: primary, secondary, archive."""
    chain: list[Provider] = []

    primary_name = os.getenv("LLM_PRIMARY", "gemini")
    if primary_name == "gemini":
        chain.append(GeminiProvider())
    else:
        raise ValueError(f"Unknown LLM_PRIMARY: {primary_name}")

    # Secondary defaults to OpenAI (Decision Log D-05). Skip silently if
    # OPENAI_API_KEY is not configured — archive still catches downstream.
    # Set LLM_SECONDARY="" to disable the secondary tier entirely.
    secondary_name = os.getenv("LLM_SECONDARY", "openai")
    if secondary_name == "openai":
        if os.getenv("OPENAI_API_KEY"):
            from .providers.openai import OpenAIProvider
            chain.append(OpenAIProvider())
        else:
            print("[runner] LLM_SECONDARY=openai but OPENAI_API_KEY not set; skipping")
    elif secondary_name == "anthropic":
        from .providers.anthropic import AnthropicProvider  # noqa: F401  optional
        chain.append(AnthropicProvider())
    elif secondary_name and secondary_name != "":
        raise ValueError(f"Unknown LLM_SECONDARY: {secondary_name}")

    chain.append(ArchiveProvider())  # always last
    return chain


def _archive_path(timeframe: str) -> Path:
    """Per-cycle archive path for a generated summary text."""
    from datetime import datetime
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    archive_dir = Path(f"data/archive/{year}/{month}")
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir / f"summary_{ARCHIVE_LABEL[timeframe]}_{timestamp}.txt"


def run_inference(timeframe: str, summary_json_text: str) -> Path:
    """Generate inference for one timeframe; write result to disk; return output path.

    On all-providers failure: raises RuntimeError. ArchiveProvider is always
    the last entry in the chain and never raises, so this should only happen
    if validation rejects the archive's output (e.g., placeholder is too
    short to pass validators) — extremely rare.
    """
    system_prompt = (
        HUSTLE_BASE_PROMPT + "\n\n" + TIMEFRAME_PROMPTS[timeframe]
    ).strip()
    request = GenerationRequest(
        system_prompt=system_prompt,
        user_prompt=summary_json_text,
        timeframe=timeframe,
    )

    providers = get_providers()
    last_error: Exception | None = None
    for provider in providers:
        try:
            result = provider.generate(request)
            # Archive provider's placeholder output may not satisfy strict
            # validation (no real closing line). Skip validation for archive
            # results so the cascade always reaches a usable fallback.
            if provider.name != "archive":
                validate_output(result.text)
            output_path = OUTPUT_MAP[timeframe]
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.text, encoding="utf-8")

            # Archive the result so future cascades have material to fall
            # back to. Only archive non-archive (real or OpenAI) outputs —
            # archiving an archive output would defeat the notice-compounding
            # filter in ArchiveProvider.
            if provider.name != "archive":
                archive_p = _archive_path(timeframe)
                archive_p.write_text(result.text, encoding="utf-8")
                print(f"[{timeframe}] Generated via {result.provider_name} "
                      f"({result.model_name}) → archived to {archive_p.name}")
            else:
                print(f"[{timeframe}] Served from archive ({result.model_name}) "
                      f"— pipeline degraded, not archiving fallback output")
            return output_path
        except (ProviderError, ValidationError) as e:
            print(f"[{timeframe}] {provider.name} failed: {e}")
            last_error = e

    # Should be unreachable: ArchiveProvider always returns something.
    raise RuntimeError(f"All providers exhausted for {timeframe}: {last_error}")
