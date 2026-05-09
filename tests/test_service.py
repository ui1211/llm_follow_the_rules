from src.service import GenerationConfig, RuleFollowingGenerator, quality_check


class QueueClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.responses.pop(0)


def test_quality_check_fails_before_rule_check_when_loop_detected() -> None:
    checker = QueueClient(['{"ok": true, "reason": "should not be used"}'])
    output = "a" * 80 * 3

    result = quality_check(output, "rule", checker, abnormal_size=1)

    assert result.ok is False
    assert result.reason.startswith("loop_detected:")
    assert checker.prompts == []


def test_rule_following_generator_returns_first_accepted_output() -> None:
    generator_client = QueueClient(["accepted"])
    checker_client = QueueClient(['{"ok": true, "reason": "valid"}'])
    generator = RuleFollowingGenerator(
        generator_client,
        checker_client,
        restart_hook=None,
        config=GenerationConfig(max_retry=3, abnormal_size=5000),
    )

    assert generator.ask("prompt", "rule") == "accepted"
    assert len(generator_client.prompts) == 1
    assert len(checker_client.prompts) == 1


def test_rule_following_generator_retries_after_rejected_output() -> None:
    generator_client = QueueClient(["bad", "good"])
    checker_client = QueueClient(
        [
            '{"ok": false, "reason": "format mismatch"}',
            '{"ok": true, "reason": "valid"}',
        ]
    )
    restart_reasons: list[str] = []
    generator = RuleFollowingGenerator(
        generator_client,
        checker_client,
        restart_hook=restart_reasons.append,
        config=GenerationConfig(max_retry=2, abnormal_size=5000),
    )

    assert generator.ask("prompt", "rule") == "good"
    assert restart_reasons == ["rule_failed: format mismatch"]
    assert "前回の出力は品質チェックに失敗しました" in generator_client.prompts[1]


def test_rule_following_generator_returns_error_after_retry_limit() -> None:
    generator = RuleFollowingGenerator(
        QueueClient(["bad"]),
        QueueClient(['{"ok": false, "reason": "invalid"}']),
        restart_hook=None,
        config=GenerationConfig(max_retry=1, abnormal_size=5000),
    )

    assert generator.ask("prompt", "rule") == "ERROR: RETRY LIMIT EXCEEDED"
