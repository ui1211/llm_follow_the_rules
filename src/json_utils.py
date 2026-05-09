"""JSON extraction helpers for noisy LLM responses."""

from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(raw: str) -> dict[str, Any]:
    """Parse a JSON object, allowing extra text around the object."""

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        return parsed

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("json_object_not_found")

    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("json_object_not_found")
    return parsed
