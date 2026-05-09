from loguru import logger

from src.service import GenerationConfig, RuleFollowingGenerator, ask_llm, quality_check


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


def test_rule_following_generator_returns_structured_result() -> None:
    generator = RuleFollowingGenerator(
        QueueClient(["accepted"]),
        QueueClient(['{"ok": true, "reason": "valid"}']),
        restart_hook=None,
    )

    result = generator.generate("prompt", "rule")

    assert result.ok is True
    assert result.text == "accepted"
    assert result.error is None
    assert result.attempts == 1
    assert result.reason == "all_checks_passed"
    assert [event.stage for event in result.events] == [
        "attempt_start",
        "generation",
        "quality_check",
    ]
    assert result.events[-1].ok is True


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
    assert "The previous output failed the quality check." in generator_client.prompts[1]


def test_rule_following_generator_does_not_restart_by_default() -> None:
    generator = RuleFollowingGenerator(
        QueueClient(["bad", "good"]),
        QueueClient(
            [
                '{"ok": false, "reason": "format mismatch"}',
                '{"ok": true, "reason": "valid"}',
            ]
        ),
        config=GenerationConfig(max_retry=2, abnormal_size=5000),
    )

    assert generator.ask("prompt", "rule") == "good"


def test_rule_following_generator_returns_error_after_retry_limit() -> None:
    generator = RuleFollowingGenerator(
        QueueClient(["bad"]),
        QueueClient(['{"ok": false, "reason": "invalid"}']),
        restart_hook=None,
        config=GenerationConfig(max_retry=1, abnormal_size=5000),
    )

    assert generator.ask("prompt", "rule") == "ERROR: RETRY LIMIT EXCEEDED"


def test_ask_llm_keeps_string_compatibility() -> None:
    result = ask_llm(
        "prompt",
        "rule",
        client=QueueClient(["accepted"]),
        checker_client=QueueClient(['{"ok": true, "reason": "valid"}']),
        restart_hook=None,
    )

    assert result == "accepted"


def test_ask_llm_display_final_logs_only_summary() -> None:
    messages: list[str] = []
    sink_id = logger.add(lambda message: messages.append(str(message)), format="{message}")
    result = ask_llm(
        "prompt",
        "rule",
        client=QueueClient(["accepted"]),
        checker_client=QueueClient(['{"ok": true, "reason": "valid"}']),
        display="final",
    )
    logger.remove(sink_id)

    assert result == "accepted"
    assert len(messages) == 1
    assert "[PASS] attempts=1 reason=all_checks_passed" in messages[0]


def test_ask_llm_display_progress_logs_events_and_summary() -> None:
    messages: list[str] = []
    sink_id = logger.add(lambda message: messages.append(str(message)), format="{message}")
    result = ask_llm(
        "prompt",
        "rule",
        client=QueueClient(["bad", "good"]),
        checker_client=QueueClient(
            [
                '{"ok": false, "reason": "format mismatch"}',
                '{"ok": true, "reason": "valid"}',
            ]
        ),
        max_retry=2,
        display="progress",
    )
    logger.remove(sink_id)

    output = "\n".join(messages)
    assert result == "good"
    assert "stage=attempt_start reason=1/2" in output
    assert "stage=quality_check reason=rule_failed: format mismatch" in output
    assert "[PASS] attempts=2 reason=all_checks_passed" in output
