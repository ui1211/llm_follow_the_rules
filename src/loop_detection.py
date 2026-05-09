"""Detect common local-LLM repetition failures."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class LoopCheckResult:
    is_loop: bool
    reason: str


def normalize_text(text: str | None) -> str:
    """Normalize text for repetition checks."""

    return re.sub(r"\s+", "", text or "")


def has_repeated_block(
    text: str | None,
    *,
    min_block_len: int = 80,
    repeat_threshold: int = 3,
) -> LoopCheckResult:
    normalized = normalize_text(text)

    if len(normalized) < min_block_len * repeat_threshold:
        return LoopCheckResult(False, "text_too_short")

    for block_len in (80, 120, 200, 400, 800):
        if len(normalized) < block_len * repeat_threshold:
            continue

        seen: dict[str, int] = {}
        for i in range(0, len(normalized) - block_len + 1, block_len):
            block = normalized[i : i + block_len]
            seen[block] = seen.get(block, 0) + 1
            if seen[block] >= repeat_threshold:
                return LoopCheckResult(
                    True,
                    f"repeated_exact_block_len={block_len}, count={seen[block]}",
                )

    return LoopCheckResult(False, "no_repeated_block")


def has_tail_loop(
    text: str | None,
    *,
    window: int = 800,
    threshold: float = 0.92,
) -> LoopCheckResult:
    normalized = normalize_text(text)

    if len(normalized) < window * 2:
        return LoopCheckResult(False, "text_too_short")

    tail1 = normalized[-window:]
    tail2 = normalized[-window * 2 : -window]
    similarity = SequenceMatcher(None, tail1, tail2).ratio()

    if similarity >= threshold:
        return LoopCheckResult(True, f"tail_similarity={similarity:.3f}")

    return LoopCheckResult(False, f"tail_similarity={similarity:.3f}")


def detect_loop(text: str | None, *, abnormal_size: int = 5000) -> LoopCheckResult:
    """Run loop checks only for unusually long responses."""

    if len(text or "") < abnormal_size:
        return LoopCheckResult(False, "length_under_threshold")

    block_result = has_repeated_block(text)
    if block_result.is_loop:
        return block_result

    tail_result = has_tail_loop(text)
    if tail_result.is_loop:
        return tail_result

    return LoopCheckResult(False, "no_loop_detected")
