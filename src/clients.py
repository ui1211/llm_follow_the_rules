"""LLM client adapters."""

from __future__ import annotations

import json
import random
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "fredrezones55/Gemma-4-Uncensored-HauhauCS-Aggressive:e4b"


class LLMClient(Protocol):
    """Minimal interface required by the rule-following service."""

    def generate(self, prompt: str) -> str:
        """Generate text for a prompt."""


@dataclass(frozen=True)
class OllamaGenerateClient:
    """HTTP client for Ollama's non-streaming generate endpoint."""

    model: str = DEFAULT_MODEL
    url: str = DEFAULT_OLLAMA_URL
    timeout: float = 30.0

    def generate(self, prompt: str) -> str:
        seed = random.randint(0, 2**31 - 1)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": 0,
            "options": {"seed": seed},
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
