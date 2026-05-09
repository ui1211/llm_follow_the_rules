"""High-level rule-following generation workflow."""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from typing import Callable

from src.clients import LLMClient, OllamaGenerateClient
from src.loop_detection import detect_loop
from src.rule_checker import RuleCheckResult, check_rule_with_llm

logger = logging.getLogger(__name__)
RestartHook = Callable[[str], None]


@dataclass(frozen=True)
class QualityCheckResult:
    ok: bool
    reason: str


@dataclass(frozen=True)
class GenerationConfig:
    max_retry: int = 3
    abnormal_size: int = 5000


def restart_ollama_process(_: str) -> None:
    """Best-effort Windows Ollama restart hook used after rejected output."""

    subprocess.run(["taskkill", "/IM", "ollama.exe", "/F"], check=False)
    time.sleep(1.5)


def build_generation_prompt(prompt: str, system_rule: str) -> str:
    return f"""
[System Rule]
{system_rule}

[User Input]
{prompt}

[Output Requirements]
- System Ruleを厳守すること
- 同じ文、同じ段落、同じ構造を繰り返さないこと
- 必要以上に長くしないこと
"""


def build_retry_prompt(base_prompt: str, reason: str) -> str:
    hint = ""
    if "tail_similarity" in reason or "repeated" in reason:
        hint = "出力の一部が繰り返されています。重複を削除してください。"
    elif "json" in reason:
        hint = "JSON形式が崩れています。JSONのみを厳密に出力してください。"
    elif "empty" in reason:
        hint = "出力が空です。必ず内容を生成してください。"
    elif "rule" in reason:
        hint = "System Rule違反があります。特に形式と余計な出力に注意してください。"

    return f"""
前回の出力は品質チェックに失敗しました。

[失敗理由]
{reason}

[補足]
{hint}

[修正指示]
- System Ruleを優先してください
- 同じ文や段落を繰り返さないでください
- 出力を簡潔にしてください
- JSONなど指定形式がある場合は、その形式だけを返してください

{base_prompt}
"""


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
        restart_hook: RestartHook | None = restart_ollama_process,
        config: GenerationConfig | None = None,
    ) -> None:
        self.generator_client = generator_client
        self.checker_client = checker_client or generator_client
        self.restart_hook = restart_hook
        self.config = config or GenerationConfig()

    def ask(self, prompt: str, system_rule: str) -> str:
        base_prompt = build_generation_prompt(prompt, system_rule)
        current_prompt = base_prompt

        for attempt in range(1, self.config.max_retry + 1):
            logger.info("generation attempt %s/%s", attempt, self.config.max_retry)
            try:
                text = self.generator_client.generate(current_prompt)
            except Exception as exc:
                logger.exception("generation failed")
                return f"ERROR: GENERATION FAILED: {exc}"

            if not text.strip():
                reason = "empty_output"
                current_prompt = build_retry_prompt(base_prompt, reason)
                continue

            result = quality_check(
                text,
                system_rule,
                self.checker_client,
                abnormal_size=self.config.abnormal_size,
            )
            if result.ok:
                logger.info("final output accepted on attempt %s", attempt)
                return text

            logger.warning("retrying after failed quality check: %s", result.reason)
            if self.restart_hook is not None:
                self.restart_hook(result.reason)
            current_prompt = build_retry_prompt(base_prompt, result.reason)

        logger.error("final output rejected: retry limit exceeded")
        return "ERROR: RETRY LIMIT EXCEEDED"


def ask_llm(
    prompt: str,
    system_rule: str,
    *,
    client: LLMClient | None = None,
    checker_client: LLMClient | None = None,
    max_retry: int = 3,
    abnormal_size: int = 5000,
    restart_hook: RestartHook | None = restart_ollama_process,
) -> str:
    """Compatibility function for existing callers."""

    generator = RuleFollowingGenerator(
        generator_client=client or OllamaGenerateClient(),
        checker_client=checker_client,
        restart_hook=restart_hook,
        config=GenerationConfig(max_retry=max_retry, abnormal_size=abnormal_size),
    )
    return generator.ask(prompt, system_rule)
