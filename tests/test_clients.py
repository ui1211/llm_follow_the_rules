import json
from urllib.error import HTTPError

import pytest

from llm_follow_the_rules.clients import OllamaGenerateClient, OllamaOptions


class FakeResponse:
    def __init__(self, body: dict[str, str]) -> None:
        self.body = json.dumps(body).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_ollama_generate_client_uses_configured_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))  # type: ignore[attr-defined]
        return FakeResponse({"response": "ok"})

    monkeypatch.setattr("llm_follow_the_rules.clients.urllib.request.urlopen", fake_urlopen)
    client = OllamaGenerateClient(
        model="model-a",
        timeout=12,
        options=OllamaOptions(temperature=0.2, repeat_penalty=1.3, num_predict=128, seed=7),
    )

    assert client.generate("prompt") == "ok"
    assert captured["timeout"] == 12
    assert captured["payload"] == {
        "model": "model-a",
        "prompt": "prompt",
        "stream": False,
        "keep_alive": 0,
        "options": {
            "temperature": 0.2,
            "repeat_penalty": 1.3,
            "num_predict": 128,
            "seed": 7,
        },
    }


def test_ollama_generate_client_reports_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        raise HTTPError("url", 500, "server error", {}, None)

    monkeypatch.setattr("llm_follow_the_rules.clients.urllib.request.urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="HTTP 500"):
        OllamaGenerateClient().generate("prompt")
