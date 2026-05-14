"""Rule-compliance checking via an injected LLM client."""

from __future__ import annotations

import json
from dataclasses import dataclass

from llm_follow_the_rules.clients import LLMClient
from llm_follow_the_rules.prompt_templates import render_template


@dataclass(frozen=True)
class RuleCheckResult:
    ok: bool
    reason: str


def build_rule_check_prompt(output: str, system_rule: str) -> str:
    """Build the prompt used to ask the checker LLM for a text verdict."""

    return render_template("rule_check.md", output=output, system_rule=system_rule)


def _split_verdict(raw: str) -> tuple[str, str]:
    text = raw.strip()
    if not text:
        return "", "empty checker response"

    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if ":" in first_line:
        verdict, reason = first_line.split(":", 1)
        return verdict.strip().lower(), reason.strip() or "no reason provided"
    return first_line.strip().lower(), "no reason provided"


def _parse_legacy_json_verdict(raw: str) -> RuleCheckResult | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    ok = parsed.get("ok")
    if not isinstance(ok, bool):
        return RuleCheckResult(False, "rule_check_invalid_ok_type")

    return RuleCheckResult(
        ok=ok,
        reason=str(parsed.get("reason", "no reason provided")),
    )


def check_rule_with_llm(
    output: str,
    system_rule: str,
    client: LLMClient,
) -> RuleCheckResult:
    """Return a structured rule-check result from the checker LLM."""

    raw = client.generate(build_rule_check_prompt(output, system_rule))
    legacy_result = _parse_legacy_json_verdict(raw)
    if legacy_result is not None:
        return legacy_result

    verdict, reason = _split_verdict(raw)
    if verdict in {"pass", "ok", "true"}:
        return RuleCheckResult(True, reason)
    if verdict in {"fail", "ng", "false"}:
        return RuleCheckResult(False, reason)

    return RuleCheckResult(False, "rule_check_unparseable")
