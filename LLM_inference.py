"""Entry point for LLM inference.

Phase 2.4 refactor: the previous monolithic module is now a thin shim
over the `llm/` package, which implements the cascade:

    Gemini (primary) → OpenAI (default secondary, per Decision Log D-05)
    → Archive (always-succeeds floor)

Per-timeframe isolation: a failure on one timeframe does NOT prevent
the others from generating. The script returns a non-zero exit code
ONLY if every provider in the chain fails for at least one timeframe
(extremely unlikely, since ArchiveProvider always returns something
after the first-ever successful run).
"""
import sys
from pathlib import Path
from llm.runner import run_inference, OUTPUT_MAP


def main() -> int:
    data_path = Path("data/summary_results_current.json")
    if not data_path.exists():
        print("FATAL: Missing data/summary_results_current.json", file=sys.stderr)
        return 1

    summary_text = data_path.read_text(encoding="utf-8")
    print(f"Loaded summary JSON ({len(summary_text)} chars)")

    failures = 0
    for timeframe in OUTPUT_MAP.keys():
        try:
            run_inference(timeframe, summary_text)
        except Exception as e:
            print(f"FATAL: All providers failed for {timeframe}: {e}", file=sys.stderr)
            failures += 1

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
