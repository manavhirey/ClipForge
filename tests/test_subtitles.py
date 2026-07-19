import pytest

from clipforge.stages.subtitles import build_ass, format_ass_timestamp


def test_format_ass_timestamp():
    assert format_ass_timestamp(0.0) == "0:00:00.00"
    assert format_ass_timestamp(65.5) == "0:01:05.50"
    assert format_ass_timestamp(3661.25) == "1:01:01.25"


def test_build_ass_creates_dialogue_line_per_word():
    words = [
        {"word": "hi", "start": 0.0, "end": 0.2},
        {"word": "you", "start": 0.3, "end": 0.6},
    ]

    result = build_ass(words)

    assert "Dialogue: 0,0:00:00.00,0:00:00.20,Word,HI" in result
    assert "Dialogue: 0,0:00:00.30,0:00:00.60,Word,YOU" in result
    assert "[Script Info]" in result


def test_build_ass_raises_on_empty_input():
    with pytest.raises(ValueError, match="No word timestamps"):
        build_ass([])
