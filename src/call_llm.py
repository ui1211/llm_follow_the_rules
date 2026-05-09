"""Backward-compatible public API for rule-following LLM generation."""

from __future__ import annotations

from src.clients import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, OllamaGenerateClient
from src.files import load_md
from src.service import ask_llm

MODEL = DEFAULT_MODEL
URL = DEFAULT_OLLAMA_URL

__all__ = ["MODEL", "URL", "OllamaGenerateClient", "ask_llm", "load_md"]
