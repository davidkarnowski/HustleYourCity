"""Google Gemini provider (Google AI Studio API).

Lifted from the pre-Phase-2.4 monolithic LLM_inference.py and adapted to
the Provider interface. Behavior is intentionally identical to the
previous implementation: 5 attempts with exponential backoff (2/4/8/16/32 s)
on 429/500/503; on persistent failure, raises ProviderError so the runner
can cascade to the secondary.
"""
import os
import time
import requests
from .base import Provider, GenerationRequest, GenerationResult, ProviderError

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
RETRY_STATUS = (429, 500, 503)


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, model: str | None = None):
        # Default model from env so a future model bump is config-only.
        self.model = model or os.getenv(
            "LLM_PRIMARY_MODEL", "gemini-3.1-flash-lite-preview"
        )
        self.api_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        if not self.api_key:
            raise ProviderError("Missing GOOGLE_AI_STUDIO_API_KEY env var")

    def generate(self, request: GenerationRequest) -> GenerationResult:
        url = f"{GEMINI_API_BASE}/{self.model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        payload = {
            "contents": [{"parts": [
                {"text": request.system_prompt + "\n\nYou will now receive the JSON data."},
                {"text": request.user_prompt},
            ]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }

        for attempt in range(1, 6):
            try:
                res = requests.post(url, headers=headers, json=payload, timeout=90)
                if res.status_code in RETRY_STATUS:
                    wait = 2 ** attempt
                    print(f"[gemini] HTTP {res.status_code}, retry in {wait}s (attempt {attempt}/5)")
                    time.sleep(wait)
                    continue
                if res.status_code != 200:
                    raise ProviderError(
                        f"Gemini API {res.status_code}: {res.text[:300]}"
                    )
                data = res.json()
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except (KeyError, IndexError) as e:
                    raise ProviderError(f"Gemini response missing text: {e}")
                return GenerationResult(
                    text=text,
                    provider_name=self.name,
                    model_name=self.model,
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                wait = 2 ** attempt
                print(f"[gemini] network error: {e}, retry in {wait}s (attempt {attempt}/5)")
                time.sleep(wait)

        raise ProviderError("Gemini exhausted retries")
