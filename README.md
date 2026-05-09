# llm_follow_the_rules

Low-end local LLMs can drift, repeat themselves, or ignore detailed output rules. This library wraps generation with rule-based self-checking, retry prompts, loop detection, and optional progress logging.

## Install

Python 3.12 or later is required.

For local development:

```powershell
uv sync
```

Install from a Git repository in another project:

```powershell
uv add "llm-follow-the-rules @ git+https://github.com/<owner>/<repo>.git"
```

Install from this local Git repository:

```powershell
uv add "llm-follow-the-rules @ git+file:///C:/Users/yutou/Desktop/work/tools/llm_follow_the_rules"
```

## Ollama

By default, the library uses Ollama's generate API.

- URL: `http://localhost:11434/api/generate`
- model: `qwen3.5:9b`

Start Ollama and pull the model you want to use.

```powershell
ollama serve
ollama pull qwen3.5:9b
```

## Run

The main API is `ask_llm`. Pass a user prompt and rule Markdown. The generated output is checked for repetition and rule compliance. Failed outputs are retried.

```powershell
uv run python -c "from llm_follow_the_rules import ask_llm, load_md; rule = load_md('examples/simple_rule.md'); print(ask_llm('write one page scenario', rule))"
```

Use `OllamaGenerateClient` to change the model or endpoint.

```python
from llm_follow_the_rules import OllamaGenerateClient, ask_llm, load_md

rule = load_md("examples/simple_rule.md")
client = OllamaGenerateClient(
    model="your-model-name",
    url="http://localhost:11434/api/generate",
)

result = ask_llm("write one page scenario", rule, client=client)
print(result)
```

## ask_llm Arguments

`ask_llm` is the backward-compatible string-returning API.

```python
ask_llm(
    prompt: str,
    system_rule: str,
    *,
    client: LLMClient | None = None,
    checker_client: LLMClient | None = None,
    max_retry: int = 3,
    abnormal_size: int = 5000,
    restart_hook: Callable[[str], None] | None = None,
    display: Literal["none", "final", "progress"] = "none",
) -> str
```

| Argument | Required | Description |
| --- | --- | --- |
| `prompt` | Yes | User request passed to the generation LLM. |
| `system_rule` | Yes | Rule text, usually loaded from a Markdown file with `load_md`. The generated output is checked against this rule. |
| `client` | No | Generation LLM client. If omitted, `OllamaGenerateClient()` is used. |
| `checker_client` | No | LLM client used for rule checking. If omitted, the same client as `client` is used. |
| `max_retry` | No | Maximum number of generation attempts, including the first attempt. |
| `abnormal_size` | No | Output length threshold for expensive loop checks. Short repeated lines are checked regardless of this value. |
| `restart_hook` | No | Optional callback called after a failed quality check. It receives the failure reason. Defaults to `None`, so no process restart is performed. |
| `display` | No | Controls loguru display logs. `none` emits no display logs, `final` logs only the final summary, and `progress` logs per-attempt progress plus the final summary. |

Return value:

- On success, returns the accepted generated text.
- On failure, returns a string beginning with `ERROR:`.

For structured success/failure details such as `ok`, `attempts`, `reason`, `error`, and per-attempt `events`, use `RuleFollowingGenerator.generate()` instead of `ask_llm`.

Display examples:

```python
ask_llm("write one page scenario", rule, display="final")
ask_llm("write one page scenario", rule, display="progress")
```

### ask_llm 引数説明

`ask_llm` は既存互換のため、成功時も失敗時も文字列を返します。

| 引数 | 必須 | 説明 |
| --- | --- | --- |
| `prompt` | 必須 | 生成用 LLM に渡すユーザー要求です。 |
| `system_rule` | 必須 | 生成結果が従うべきルール本文です。通常は `load_md` で Markdown ファイルから読み込みます。 |
| `client` | 任意 | 生成用 LLM クライアントです。省略時は `OllamaGenerateClient()` を使います。 |
| `checker_client` | 任意 | ルール準拠判定に使う LLM クライアントです。省略時は `client` と同じクライアントを使います。 |
| `max_retry` | 任意 | 最大生成試行回数です。初回生成も回数に含みます。 |
| `abnormal_size` | 任意 | 高コストなループ検出を実行する出力長のしきい値です。短い行の繰り返しは、この値に関係なく検出します。 |
| `restart_hook` | 任意 | 品質チェック失敗後に呼ばれる任意のコールバックです。失敗理由の文字列を受け取ります。既定値は `None` なので、プロセス再起動などの副作用は発生しません。 |
| `display` | 任意 | `loguru` による表示ログのモードです。`none` は表示ログを出しません。`final` は最終結果だけをログ出力します。`progress` は試行開始、生成完了、品質チェック結果、最終結果をログ出力します。 |

戻り値:

- 成功時は、品質チェックを通過した生成テキストを返します。
- 失敗時は、`ERROR:` で始まる文字列を返します。

成功/失敗、試行回数、失敗理由、各試行の履歴 `events` などを構造化して扱いたい場合は、`ask_llm` ではなく `RuleFollowingGenerator.generate()` を使ってください。

## Prompt Templates

Fixed instructions sent to the LLM are bundled as English templates under `src/llm_follow_the_rules/prompts/`.

- `generation.md`: first generation prompt
- `retry.md`: retry prompt after quality-check failure
- `rule_check.md`: rule-compliance judgement prompt

Business rules and output-format requirements should be passed separately as Markdown through `ask_llm`.

## Test

Unit tests do not require Ollama.

```powershell
uv run pytest -q
```
