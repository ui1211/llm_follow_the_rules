"""LLM client adapters."""

from __future__ import annotations

import json
import random
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3.5:9b"


class LLMClient(Protocol):
    """Minimal interface required by the rule-following service."""

    def generate(self, prompt: str) -> str:
        """Generate text for a prompt."""


@dataclass(frozen=True)
class OllamaOptions:
    temperature: float | None = None
    repeat_penalty: float | None = None
    num_predict: int | None = None
    seed: int | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.repeat_penalty is not None:
            payload["repeat_penalty"] = self.repeat_penalty
        if self.num_predict is not None:
            payload["num_predict"] = self.num_predict
        payload["seed"] = self.seed if self.seed is not None else random.randint(0, 2**31 - 1)
        return payload


@dataclass(frozen=True)
class OllamaGenerateClient:
    """HTTP client for Ollama's non-streaming generate endpoint."""

    model: str = DEFAULT_MODEL
    url: str = DEFAULT_OLLAMA_URL
    timeout: float = 30.0
    options: OllamaOptions = field(default_factory=OllamaOptions)

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": 0,
            "options": self.options.to_payload(),
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Ollama request failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama response was not valid JSON") from exc

        return str(data.get("response", ""))
