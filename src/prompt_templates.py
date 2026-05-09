"""Prompt template loading and rendering."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from string import Formatter


TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "prompts"
_FORMATTER = Formatter()


@lru_cache(maxsize=None)
def load_template(name: str) -> str:
    """Load a prompt template from the project prompts directory."""

    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def render_template(name: str, **values: str) -> str:
    """Render a prompt template with strict placeholder checking."""

    template = load_template(name)
    required = {
        field_name
        for _, field_name, _, _ in _FORMATTER.parse(template)
        if field_name is not None
    }
    missing = required.difference(values)
    if missing:
        missing_fields = ", ".join(sorted(missing))
        raise ValueError(f"missing_template_values: {missing_fields}")
    return template.format(**values)
