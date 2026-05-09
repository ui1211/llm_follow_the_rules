"""File loading helpers."""

from __future__ import annotations

from pathlib import Path


def load_md(path: str | Path) -> str:
    """Load a Markdown file as UTF-8 text."""

    return Path(path).read_text(encoding="utf-8")
