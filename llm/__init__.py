"""LLM inference for HustleYourCity.

Public entry point: llm.runner.run_inference(timeframe, summary_json_text)

Default cascade (per Eval doc Decision Log D-05, 2026-04-30):
    Gemini (primary)  →  OpenAI (secondary)  →  Archive (always-succeeds floor)
"""
from .runner import run_inference, OUTPUT_MAP  # noqa: F401  re-exports
