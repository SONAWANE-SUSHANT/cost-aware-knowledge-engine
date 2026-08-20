"""
Generic LLM provider abstraction for the Cost-Aware Knowledge Engine.

Provides a common interface for LLM calls so that the rest of the system
never depends on a specific provider. OpenRouter is the default implementation.

Environment variables:
    OPENROUTER_API_KEY  — API key for OpenRouter
    OPENROUTER_MODEL    — Model identifier (default: "openai/gpt-4o-mini")

Deterministic tests must never call a real LLM. Use MockLLMProvider in tests.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class LLMUsage:
    """Token usage and estimated cost for an LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LLMResponse:
    """Standard response from any LLM provider."""

    text: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "usage": self.usage.to_dict(),
            "success": self.success,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Abstract Provider
# ---------------------------------------------------------------------------


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send a prompt to the LLM and return the response."""

# ---------------------------------------------------------------------------
# OpenRouter Provider
# ---------------------------------------------------------------------------


OPENROUTER_DEFAULT_MODEL = "openai/gpt-4o-mini"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Approximate cost per 1K tokens (USD) for common models
MODEL_COST_ESTIMATES: dict[str, tuple[float, float]] = {
    "openai/gpt-4o-mini": (0.00015, 0.00060),
    "openai/gpt-4o": (0.00250, 0.01000),
    "openai/gpt-3.5-turbo": (0.00050, 0.00150),
    "anthropic/claude-3-haiku": (0.00025, 0.00125),
    "anthropic/claude-3-sonnet": (0.00300, 0.01500),
    "anthropic/claude-3-opus": (0.01500, 0.07500),
    "google/gemini-pro": (0.00025, 0.00050),
    "meta-llama/llama-3-70b": (0.00059, 0.00079),
    "mistral/mistral-7b": (0.00020, 0.00060),
}

DEFAULT_INPUT_COST_PER_1K = 0.00050
DEFAULT_OUTPUT_COST_PER_1K = 0.00150


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate USD cost for an LLM call based on model and token counts."""
    estimates = MODEL_COST_ESTIMATES.get(model)
    if estimates is None:
        for key, vals in MODEL_COST_ESTIMATES.items():
            if model.startswith(key.split("/")[0]):
                estimates = vals
                break
    if estimates is None:
        estimates = (DEFAULT_INPUT_COST_PER_1K, DEFAULT_OUTPUT_COST_PER_1K)

    input_cost = (prompt_tokens / 1000) * estimates[0]
    output_cost = (completion_tokens / 1000) * estimates[1]
    return round(input_cost + output_cost, 8)
class OpenRouterProvider(LLMProvider):
    """LLM provider that calls OpenRouter's unified API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("OPENROUTER_MODEL", OPENROUTER_DEFAULT_MODEL)
        self.timeout = timeout

        if not self.api_key:
            logger.warning(
                "OPENROUTER_API_KEY is not set. LLM calls will fail gracefully."
            )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                text="",
                success=False,
                error="OPENROUTER_API_KEY is not configured",
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    OPENROUTER_BASE_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )

            if response.status_code != 200:
                error_body = response.text
                try:
                    error_data = response.json()
                    error_body = error_data.get("error", {}).get(
                        "message", response.text
                    )
                except (json.JSONDecodeError, KeyError):
                    pass

                logger.error(
                    "OpenRouter API error (status=%s): %s",
                    response.status_code,
                    error_body,
                )
                return LLMResponse(
                    text="",
                    success=False,
                    error=f"OpenRouter API error (HTTP {response.status_code}): {error_body}",
                )

            data = response.json()
            choice = data.get("choices", [{}])[0]
            text = choice.get("message", {}).get("content", "")

            usage_data = data.get("usage", {})
            prompt_tokens = usage_data.get("prompt_tokens", 0)
            completion_tokens = usage_data.get("completion_tokens", 0)
            total_tokens = usage_data.get("total_tokens", 0)

            estimated_cost_value = estimate_cost(
                self.model, prompt_tokens, completion_tokens
            )

            usage = LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost_value,
            )

            return LLMResponse(text=text, usage=usage, success=True)

        except httpx.TimeoutException:
            logger.error("OpenRouter request timed out after %ss", self.timeout)
            return LLMResponse(
                text="",
                success=False,
                error=f"Request timed out after {self.timeout}s",
            )
        except httpx.RequestError as exc:
            logger.error("OpenRouter request failed: %s", exc)
            return LLMResponse(
                text="",
                success=False,
                error=f"Request failed: {exc}",
            )
        except Exception as exc:
            logger.error("Unexpected LLM error: %s", exc)
            return LLMResponse(
                text="",
                success=False,
                error=f"Unexpected error: {exc}",
            )


# ---------------------------------------------------------------------------
# Mock Providers (for deterministic tests)
# ---------------------------------------------------------------------------


class MockLLMProvider(LLMProvider):
    """Mock LLM provider that returns canned responses. Never calls an API."""

    def __init__(self, response_text: str = "Mocked LLM answer"):
        self.response_text = response_text
        self.last_prompt: Optional[str] = None
        self.call_count = 0

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        self.last_prompt = prompt
        self.call_count += 1
        return LLMResponse(
            text=self.response_text,
            usage=LLMUsage(
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(self.response_text.split()),
                total_tokens=len(prompt.split()) + len(self.response_text.split()),
                estimated_cost=0.0,
            ),
            success=True,
        )


class FailingLLMProvider(LLMProvider):
    """Mock LLM provider that simulates a failure. Never calls an API."""

    def __init__(self, error_message: str = "Simulated LLM failure"):
        self.error_message = error_message

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        return LLMResponse(
            text="",
            success=False,
            error=self.error_message,
        )