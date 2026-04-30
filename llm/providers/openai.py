"""OpenAI provider (Chat Completions API).

Default secondary in the cascade (per Eval doc Decision Log D-05,
2026-04-30). Activated automatically when LLM_SECONDARY=openai (the
default) and OPENAI_API_KEY is set as a GitHub Actions secret.

Rationale: Gemini preview-tier 503 service-overload events were
observed in production on 2026-04-30 and confirmed by the Google AI
Studio dashboard ("This model is currently experiencing high demand").
Cascading to OpenAI mitigates without changing the user-visible content
path or requiring intervention.
"""
import os
import time
import requests
from .base import Provider, GenerationRequest, GenerationResult, ProviderError

ENDPOINT = "https://api.openai.com/v1/chat/completions"
RETRY_STATUS = (429, 500, 502, 503, 504)


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, model: str | None = None):
        # gpt-4o-mini is the safe, cheap, capacity-rich default for a
        # backup role. Override via LLM_SECONDARY_MODEL env var if a newer
        # cheap GA model becomes preferred.
        self.model = model or os.getenv("LLM_SECONDARY_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ProviderError("Missing OPENAI_API_KEY env var")

    def generate(self, request: GenerationRequest) -> GenerationResult:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user",   "content": request.user_prompt},
            ],
        }
        for attempt in range(1, 6):
            try:
                res = requests.post(ENDPOINT, headers=headers, json=payload, timeout=90)
                if res.status_code in RETRY_STATUS:
                    wait = 2 ** attempt
                    print(f"[openai] HTTP {res.status_code}, retry in {wait}s (attempt {attempt}/5)")
                    time.sleep(wait)
                    continue
                if res.status_code != 200:
                    raise ProviderError(f"OpenAI API {res.status_code}: {res.text[:300]}")
                data = res.json()
                try:
                    text = data["choices"][0]["message"]["content"].strip()
                except (KeyError, IndexError) as e:
                    raise ProviderError(f"OpenAI response missing content: {e}")
                return GenerationResult(
                    text=text,
                    provider_name=self.name,
                    model_name=self.model,
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                wait = 2 ** attempt
                print(f"[openai] network error: {e}, retry in {wait}s (attempt {attempt}/5)")
                time.sleep(wait)

        raise ProviderError("OpenAI exhausted retries")
