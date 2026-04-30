"""Archive fallback: serve the most recent archived summary for the requested timeframe.

This provider never raises ProviderError. The runner uses it as the
always-last entry in the provider chain — guaranteeing the workflow
exits 0 (the dashboards keep publishing) even if every API is down.

Notice-compounding filter: an archived file that itself starts with the
"[Note:" prefix is a previous fallback's output. Using it as a source for
a new fallback would compound prefixes across consecutive failure cycles
("[Note: ...][Note: ...]<actual content>"). The filter ensures we always
cascade back to the most recent REAL model output, however old.
"""
from pathlib import Path
from .base import Provider, GenerationRequest, GenerationResult

ARCHIVE_ROOT = Path("data/archive")

# Map runner-side timeframe key to the filename pattern fragment used by
# LLM_inference.py's archival code (e.g., summary_24hour_<timestamp>.txt).
TIMEFRAME_TO_ARCHIVE_LABEL = {
    "4hours":  "4_hour",
    "24hours": "24_hour",
    "7days":   "7_day",
    "30days":  "30_day",
    "90days":  "90_day",
}

_NOTICE_PREFIX = "[Note:"


class ArchiveProvider(Provider):
    name = "archive"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        label = TIMEFRAME_TO_ARCHIVE_LABEL.get(request.timeframe, request.timeframe)
        all_candidates = sorted(
            ARCHIVE_ROOT.rglob(f"summary_{label}_*.txt"),
            reverse=True,
        )
        # Filter out previously-served fallback outputs to prevent notice
        # compounding across cycles.
        candidates = [
            p for p in all_candidates
            if not p.read_text(encoding="utf-8").lstrip().startswith(_NOTICE_PREFIX)
        ]

        if not candidates:
            # Either first-ever cold start, or every prior cycle was itself a
            # fallback. Return a placeholder rather than raising — the runner's
            # contract is that ArchiveProvider always returns something.
            placeholder = (
                "[Note: Today's automated update is temporarily unavailable, "
                "and no archived summary exists yet. Please check back shortly.]\n\n"
                "This data summary was updated at unavailable "
                "and is based on data published by the City of Long Beach at unavailable."
            )
            return GenerationResult(
                text=placeholder,
                provider_name=self.name,
                model_name="placeholder",
            )

        most_recent = candidates[0]
        text = most_recent.read_text(encoding="utf-8")
        notice = (
            "[Note: Today's automated update is temporarily unavailable. "
            f"Showing the most recent archived summary from {most_recent.stem}.]\n\n"
        )
        return GenerationResult(
            text=notice + text,
            provider_name=self.name,
            model_name=f"archive-{most_recent.stem}",
        )
