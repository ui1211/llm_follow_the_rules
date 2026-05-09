import pytest

from src.json_utils import extract_json_object


def test_extract_json_object_from_clean_json() -> None:
    assert extract_json_object('{"ok": true, "reason": "pass"}') == {
        "ok": True,
        "reason": "pass",
    }


def test_extract_json_object_from_noisy_text() -> None:
    assert extract_json_object('prefix {"ok": false, "reason": "bad"} suffix') == {
        "ok": False,
        "reason": "bad",
    }


def test_extract_json_object_rejects_missing_object() -> None:
    with pytest.raises(ValueError, match="json_object_not_found"):
        extract_json_object("no json here")
