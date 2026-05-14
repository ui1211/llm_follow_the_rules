"""High-level rule-following generation workflow."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Literal

from loguru import logger

from llm_follow_the_rules.clients import LLMClient, OllamaGenerateClient
from llm_follow_the_rules.loop_detection import detect_loop
from llm_follow_the_rules.prompt_templates import render_template
from llm_follow_the_rules.rule_checker import RuleCheckResult, check_rule_with_llm

RestartHook = Callable[[str], None]
DisplayMode = Literal["none", "final", "progress", "detail"]


@dataclass(frozen=True)
class QualityCheckResult:
    ok: bool
    reason: str


@dataclass(frozen=True)
class GenerationResult:
    ok: bool
    text: str
    attempts: int
    reason: str
    error: str | None = None
    events: tuple["GenerationEvent", ...] = ()


@dataclass(frozen=True)
class GenerationEvent:
    attempt: int
    stage: str
    ok: bool | None
    reason: str
    response_length: int = 0
    output_preview: str = ""


@dataclass(frozen=True)
class GenerationConfig:
    max_retry: int = 3
    abnormal_size: int = 5000
    display: DisplayMode = "none"
    detail_preview_chars: int = 4000


def restart_ollama_process(_: str) -> None:
    """Best-effort Windows Ollama restart hook used after rejected output."""

    subprocess.run(["taskkill", "/IM", "ollama.exe", "/F"], check=False)
    time.sleep(1.5)


def build_generation_prompt(prompt: str, system_rule: str) -> str:
    return render_template("generation.md", prompt=prompt, system_rule=system_rule)


def build_retry_prompt(base_prompt: str, reason: str) -> str:
    hint = ""
    if "tail_similarity" in reason or "repeated" in reason:
        hint = "Part of the output is repeated. Remove duplicated content."
    elif "rule_check_parse_error" in reason:
        hint = (
            "The validator could not return a clear judgement. Regenerate the "
            "answer according to the System Rule, and do not change the output "
            "format unless the System Rule requires it."
        )
    elif "json" in reason:
        hint = "The JSON format is invalid. Return only strict JSON."
    elif "empty" in reason:
        hint = "The output was empty. Generate non-empty content."
    elif "rule" in reason:
        hint = (
            "The output violates the System Rule. Pay close attention to "
            "format and concrete output requirements."
        )

    return render_template(
        "retry.md",
        base_prompt=base_prompt,
        hint=hint,
        reason=reason,
    )


def format_generation_event(event: GenerationEvent) -> str:
    status = "INFO" if event.ok is None else "PASS" if event.ok else "FAIL"
    length = f" length={event.response_length}" if event.response_length else ""
    return (
        f"[{status}] attempt={event.attempt} stage={event.stage} "
        f"reason={event.reason}{length}"
    )


def format_generation_event_detail(event: GenerationEvent) -> str:
    message = format_generation_event(event)
    if event.output_preview:
        message = f"{message}\n[Output Preview]\n{event.output_preview}"
    return message


def format_generation_result(result: GenerationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    error = f" error={result.error}" if result.error else ""
    return (
        f"[{status}] attempts={result.attempts} reason={result.reason} "
        f"length={len(result.text)}{error}"
    )


def _preview_text(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n...<truncated {len(text) - limit} chars>"


def _log_event(event: GenerationEvent, *, detail: bool) -> None:
    message = format_generation_event_detail(event) if detail else format_generation_event(event)
    if event.ok is True:
        logger.success(message)
    elif event.ok is False:
        logger.warning(message)
    else:
        logger.info(message)


def _append_event(
    events: list[GenerationEvent],
    event: GenerationEvent,
    *,
    display: DisplayMode,
) -> None:
    events.append(event)
    if display in {"progress", "detail"}:
        _log_event(event, detail=display == "detail")


def _finish_result(result: GenerationResult, *, display: DisplayMode) -> GenerationResult:
    if display in {"final", "progress", "detail"}:
        if result.ok:
            logger.success(format_generation_result(result))
        else:
            logger.error(format_generation_result(result))
    return result


def quality_check(
    output: str,
    system_rule: str,
    checker_client: LLMClient,
    *,
    abnormal_size: int = 5000,
) -> QualityCheckResult:
    loop_result = detect_loop(output, abnormal_size=abnormal_size)
    if loop_result.is_loop:
        return QualityCheckResult(False, f"loop_detected: {loop_result.reason}")

    rule_result: RuleCheckResult = check_rule_with_llm(output, system_rule, checker_client)
    if not rule_result.ok:
        return QualityCheckResult(False, f"rule_failed: {rule_result.reason}")

    return QualityCheckResult(True, "all_checks_passed")


class RuleFollowingGenerator:
    """Generate output and retry when local quality checks fail."""

    def __init__(
        self,
        generator_client: LLMClient,
        checker_client: LLMClient | None = None,
        *,
        restart_hook: RestartHook | None = None,
        config: GenerationConfig | None = None,
    ) -> None:
        self.generator_client = generator_client
        self.checker_client = checker_client or generator_client
        self.restart_hook = restart_hook
        self.config = config or GenerationConfig()

    def generate(self, prompt: str, system_rule: str) -> GenerationResult:
        base_prompt = build_generation_prompt(prompt, system_rule)
        current_prompt = base_prompt
        events: list[GenerationEvent] = []

        for attempt in range(1, self.config.max_retry + 1):
            _append_event(
                events,
                GenerationEvent(
                    attempt=attempt,
                    stage="attempt_start",
                    ok=None,
                    reason=f"{attempt}/{self.config.max_retry}",
                ),
                display=self.config.display,
            )
            try:
                text = self.generator_client.generate(current_prompt)
            except Exception as exc:
                logger.exception("generation failed")
                error = f"GENERATION FAILED: {exc}"
                _append_event(
                    events,
                    GenerationEvent(attempt, "generation", False, error),
                    display=self.config.display,
                )
                return _finish_result(
                    GenerationResult(
                        False,
                        "",
                        attempt,
                        "generation_failed",
                        error,
                        tuple(events),
                    ),
                    display=self.config.display,
                )

            _append_event(
                events,
                GenerationEvent(
                    attempt,
                    "generation",
                    True,
                    "generation_done",
                    len(text or ""),
                    _preview_text(text or "", self.config.detail_preview_chars),
                ),
                display=self.config.display,
            )

            if not text.strip():
                reason = "empty_output"
                _append_event(
                    events,
                    GenerationEvent(
                        attempt,
                        "quality_check",
                        False,
                        reason,
                        output_preview=_preview_text(text or "", self.config.detail_preview_chars),
                    ),
                    display=self.config.display,
                )
                current_prompt = build_retry_prompt(base_prompt, reason)
                continue

            result = quality_check(
                text,
                system_rule,
                self.checker_client,
                abnormal_size=self.config.abnormal_size,
            )
            if result.ok:
                _append_event(
                    events,
                    GenerationEvent(
                        attempt,
                        "quality_check",
                        True,
                        result.reason,
                        len(text or ""),
                        _preview_text(text or "", self.config.detail_preview_chars),
                    ),
                    display=self.config.display,
                )
                return _finish_result(
                    GenerationResult(
                        True,
                        text,
                        attempt,
                        result.reason,
                        events=tuple(events),
                    ),
                    display=self.config.display,
                )

            _append_event(
                events,
                GenerationEvent(
                    attempt,
                    "quality_check",
                    False,
                    result.reason,
                    len(text or ""),
                    _preview_text(text or "", self.config.detail_preview_chars),
                ),
                display=self.config.display,
            )
            if self.restart_hook is not None:
                self.restart_hook(result.reason)
            current_prompt = build_retry_prompt(base_prompt, result.reason)

        error = "RETRY LIMIT EXCEEDED"
        return _finish_result(
            GenerationResult(
                False,
                "",
                self.config.max_retry,
                "retry_limit_exceeded",
                error,
                tuple(events),
            ),
            display=self.config.display,
        )

    def ask(self, prompt: str, system_rule: str) -> str:
        result = self.generate(prompt, system_rule)
        if result.ok:
            return result.text
        return f"ERROR: {result.error}"


def ask_llm(
    prompt: str,
    system_rule: str,
    *,
    client: LLMClient | None = None,
    checker_client: LLMClient | None = None,
    max_retry: int = 3,
    abnormal_size: int = 5000,
    restart_hook: RestartHook | None = None,
    display: DisplayMode = "none",
    detail_preview_chars: int = 4000,
) -> str:
    """Compatibility function for existing callers."""

    generator = RuleFollowingGenerator(
        generator_client=client or OllamaGenerateClient(),
        checker_client=checker_client,
        restart_hook=restart_hook,
        config=GenerationConfig(
            max_retry=max_retry,
            abnormal_size=abnormal_size,
            display=display,
            detail_preview_chars=detail_preview_chars,
        ),
    )
    return generator.ask(prompt, system_rule)
