"""Output validation for LLM-generated text (Plan 02 Task 2.5).

The runner calls validate_output() on each provider's result. A
ValidationError causes the runner to advance to the next provider in
the chain.

Tests for these validators are deferred to Phase 2.2 (pytest setup);
the module is intentionally test-friendly via module-level constants
that can be monkeypatched.
"""
import re


class ValidationError(Exception):
    pass


# Configuration constants — module-level so tests can monkeypatch.
MIN_LENGTH = 200
MAX_LENGTH = 2500

CODE_FENCE_RE = re.compile(r"^\s*```")
REFUSAL_PATTERNS = [
    r"\bI can'?t\b",
    r"\bI'?m unable\b",
    r"\bas an AI\b",
    r"\bI cannot\b",
    r"\bI'?m sorry\b",
    r"\bI apologize\b",
]
CLOSING_LINE_RE = re.compile(
    r"This data summary was updated at .+ "
    r"and is based on data published by the City of Long Beach at .+",
    flags=re.DOTALL,
)


def is_ascii(s: str) -> bool:
    try:
        s.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def validate_output(text: str) -> None:
    """Raises ValidationError on any failed check.

    Checks (in order):
      - length within [MIN_LENGTH, MAX_LENGTH]
      - does not start with a code fence
      - does not contain refusal patterns ("As an AI...", "I can't...", etc.)
      - is ASCII-only (LinkedIn Little Text Format constraint)
      - contains the required closing-line timestamp marker
    """
    if not text or len(text.strip()) < MIN_LENGTH:
        raise ValidationError(f"Output too short: {len(text)} chars (min {MIN_LENGTH})")
    if len(text) > MAX_LENGTH:
        raise ValidationError(f"Output too long: {len(text)} chars (max {MAX_LENGTH})")
    if CODE_FENCE_RE.match(text):
        raise ValidationError("Output starts with a code fence")
    for pattern in REFUSAL_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise ValidationError(f"Output contains refusal pattern: {pattern}")
    if not is_ascii(text):
        non_ascii = sorted({c for c in text if ord(c) > 127})
        raise ValidationError(f"Output contains non-ASCII: {non_ascii[:10]}")
    if not CLOSING_LINE_RE.search(text):
        raise ValidationError("Output missing required closing-line timestamp format")
