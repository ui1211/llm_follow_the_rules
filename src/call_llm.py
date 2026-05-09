"""Backward-compatible public API for rule-following LLM generation."""

from __future__ import annotations

from src.clients import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, OllamaGenerateClient, OllamaOptions
from src.files import load_md
from src.service import GenerationEvent, GenerationResult, ask_llm

MODEL = DEFAULT_MODEL
URL = DEFAULT_OLLAMA_URL

__all__ = [
    "MODEL",
    "URL",
    "GenerationEvent",
    "GenerationResult",
    "OllamaGenerateClient",
    "OllamaOptions",
    "ask_llm",
    "load_md",
]
