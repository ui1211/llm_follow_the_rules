# llm_follow_the_rules

低性能なローカル LLM にプロンプトとルール Markdown を渡し、生成結果がルールを順守しているかを自己チェックしながら再試行するための実験プロジェクトです。

## Setup

Python 3.12 以上と `uv` を使用します。

```powershell
uv sync
```

## Ollama

既定では Ollama の generate API を使用します。

- URL: `http://localhost:11434/api/generate`
- model: `fredrezones55/Gemma-4-Uncensored-HauhauCS-Aggressive:e4b`

Ollama を起動し、使用するモデルを事前に取得してください。

```powershell
ollama serve
ollama pull fredrezones55/Gemma-4-Uncensored-HauhauCS-Aggressive:e4b
```

## Run

現在の実行入口は Python API です。プロンプトとルール Markdown を渡すと、生成結果をループ検出と LLM 自己判定でチェックし、失敗時は再試行します。

```powershell
uv run python -c "from src.call_llm import ask_llm, load_md; rule = load_md('rules/scenario_rule.md'); print(ask_llm('write one page scenario', rule))"
```

モデルや Ollama URL を変える場合は `OllamaGenerateClient` を明示します。

```python
from src.call_llm import OllamaGenerateClient, ask_llm, load_md

rule = load_md("rules/scenario_rule.md")
client = OllamaGenerateClient(
    model="your-model-name",
    url="http://localhost:11434/api/generate",
)

result = ask_llm("write one page scenario", rule, client=client)
print(result)
```

## Test

単体テストは外部 Ollama に依存しません。

```powershell
uv run pytest -q
```
