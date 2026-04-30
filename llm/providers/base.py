"""Abstract base classes for LLM providers in the HustleYourCity pipeline."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GenerationRequest:
    system_prompt: str
    user_prompt: str
    timeframe: str  # one of: 4hours, 24hours, 7days, 30days, 90days
    max_tokens: int = 4096
    temperature: float = 0.3


@dataclass
class GenerationResult:
    text: str
    provider_name: str  # e.g., "gemini", "openai", "archive"
    model_name: str


class ProviderError(Exception):
    """Raised when a provider cannot fulfill a request after its own retries.

    The runner catches ProviderError and tries the next provider in the chain.
    """


class Provider(ABC):
    name: str

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Return generated text or raise ProviderError."""
        ...
