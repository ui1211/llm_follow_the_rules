from llm_follow_the_rules.rule_checker import check_rule_with_llm


class FakeClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


def test_check_rule_with_llm_returns_ok_result() -> None:
    client = FakeClient("PASS: valid")

    result = check_rule_with_llm("output", "rule", client)

    assert result.ok is True
    assert result.reason == "valid"
    assert "[System Rule]\nrule" in client.prompts[0]
    assert "[Output]\noutput" in client.prompts[0]
    assert "Return JSON only" not in client.prompts[0]


def test_check_rule_with_llm_returns_failure_result() -> None:
    result = check_rule_with_llm("output", "rule", FakeClient("FAIL: format mismatch"))

    assert result.ok is False
    assert result.reason == "format mismatch"


def test_check_rule_with_llm_fails_closed_on_unparseable_response() -> None:
    result = check_rule_with_llm("output", "rule", FakeClient("unclear response"))

    assert result.ok is False
    assert result.reason == "rule_check_unparseable"


def test_check_rule_with_llm_keeps_legacy_json_compatibility() -> None:
    result = check_rule_with_llm("output", "rule", FakeClient('{"ok": true, "reason": "valid"}'))

    assert result.ok is True
    assert result.reason == "valid"


def test_check_rule_with_llm_rejects_string_ok_value() -> None:
    result = check_rule_with_llm(
        "output",
        "rule",
        FakeClient('{"ok": "false", "reason": "invalid type"}'),
    )

    assert result.ok is False
    assert result.reason == "rule_check_invalid_ok_type"
