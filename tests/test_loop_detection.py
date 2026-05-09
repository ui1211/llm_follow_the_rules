from src.loop_detection import detect_loop, has_repeated_block, has_tail_loop


def test_detect_loop_skips_short_text() -> None:
    result = detect_loop("short", abnormal_size=5000)

    assert result.is_loop is False
    assert result.reason == "length_under_threshold"


def test_detect_loop_finds_short_line_repetition() -> None:
    result = detect_loop("same line\nsame line\nsame line", abnormal_size=5000)

    assert result.is_loop is True
    assert result.reason.startswith("repeated_line:")


def test_has_repeated_block_detects_exact_repetition() -> None:
    block = "a" * 80
    result = has_repeated_block(block * 3)

    assert result.is_loop is True
    assert "repeated_exact_block_len=80" in result.reason


def test_has_tail_loop_detects_similar_tail() -> None:
    tail = "x" * 800
    result = has_tail_loop(f"prefix{tail}{tail}")

    assert result.is_loop is True
    assert result.reason.startswith("tail_similarity=")
