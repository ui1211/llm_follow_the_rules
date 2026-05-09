"""Rule-compliance checking via an injected LLM client."""

from __future__ import annotations

from dataclasses import dataclass

from src.clients import LLMClient
from src.json_utils import extract_json_object


@dataclass(frozen=True)
class RuleCheckResult:
    ok: bool
    reason: str


def build_rule_check_prompt(output: str, system_rule: str) -> str:
    """Build the prompt used to ask the checker LLM for a JSON verdict."""

    return f"""
あなたは検査器です。
出力本文を修正せず、判定だけしてください。

[System Rule]
{system_rule}

[Output]
{output}

[判定条件]
- System Ruleに明確に違反していれば false
- 判定不能、形式崩れ、余計な説明が多い場合も false
- 問題がなければ true

[Return Format]
JSONのみを返してください。
{{"ok": true, "reason": "..." }}
"""


def check_rule_with_llm(
    output: str,
    system_rule: str,
    client: LLMClient,
) -> RuleCheckResult:
    """Return a structured rule-check result from the checker LLM."""

    raw = client.generate(build_rule_check_prompt(output, system_rule))
    try:
        parsed = extract_json_object(raw)
    except (ValueError, TypeError) as exc:
        return RuleCheckResult(False, f"rule_check_parse_error: {exc}")

    return RuleCheckResult(
        ok=bool(parsed.get("ok", False)),
        reason=str(parsed.get("reason", "no reason provided")),
    )
