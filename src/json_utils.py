"""JSON extraction helpers for noisy LLM responses."""

from __future__ import annotations

import json
from typing import Any


def extract_json_object(raw: str) -> dict[str, Any]:
    """Parse a JSON object, allowing extra text around the object."""

    decoder = json.JSONDecoder()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        return parsed

    for index, char in enumerate(raw):
        if char != "{":
            continue

        try:
            parsed, _ = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return parsed

    raise ValueError("json_object_not_found")
