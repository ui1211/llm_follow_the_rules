"""Backward-compatible public API for rule-following LLM generation."""

from __future__ import annotations

from llm_follow_the_rules.clients import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, OllamaGenerateClient, OllamaOptions
from llm_follow_the_rules.files import load_md
from llm_follow_the_rules.service import GenerationEvent, GenerationResult, ask_llm

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
