"""Prompt template loading and rendering."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from string import Formatter


_FORMATTER = Formatter()


@lru_cache(maxsize=None)
def load_template(name: str) -> str:
    """Load a bundled prompt template."""

    return (
        resources.files("llm_follow_the_rules")
        .joinpath("prompts", name)
        .read_text(encoding="utf-8")
    )


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
