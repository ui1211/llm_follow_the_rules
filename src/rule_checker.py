"""Rule-compliance checking via an injected LLM client."""

from __future__ import annotations

from dataclasses import dataclass

from src.clients import LLMClient
from src.json_utils import extract_json_object
from src.prompt_templates import render_template


@dataclass(frozen=True)
class RuleCheckResult:
    ok: bool
    reason: str


def build_rule_check_prompt(output: str, system_rule: str) -> str:
    """Build the prompt used to ask the checker LLM for a JSON verdict."""

    return render_template("rule_check.md", output=output, system_rule=system_rule)


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

    ok = parsed.get("ok", False)
    if not isinstance(ok, bool):
        return RuleCheckResult(False, "rule_check_invalid_ok_type")

    return RuleCheckResult(
        ok=ok,
        reason=str(parsed.get("reason", "no reason provided")),
    )
