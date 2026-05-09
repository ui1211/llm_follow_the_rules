import pytest

from src.prompt_templates import render_template


def test_render_template_inserts_values() -> None:
    prompt = render_template("generation.md", prompt="hello", system_rule="rule")

    assert "[System Rule]\nrule" in prompt
    assert "[User Input]\nhello" in prompt
    assert "Follow the System Rule exactly." in prompt


def test_render_template_rejects_missing_values() -> None:
    with pytest.raises(ValueError, match="missing_template_values: prompt"):
        render_template("generation.md", system_rule="rule")
