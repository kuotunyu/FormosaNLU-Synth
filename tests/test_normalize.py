"""Tests for the shared normalization and MASSIVE annotation parser."""

import pytest

from src.data.normalize import (
    contains_normalized,
    normalize_text,
    parse_annotated_utterance,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 明 天 早 上 八 點 ", "明天早上八點"),
        ("ＡＢＣ１２３", "abc123"),
        ("软件信息", "軟件信息"),
        ("Set 一個 ALARM", "set一個alarm"),
    ],
)
def test_normalize_text(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


def test_contains_normalized_across_spacing_and_width() -> None:
    assert contains_normalized("幫我設 ＡＭ ８：３０ 的鬧鐘", "AM 8:30")


def test_empty_needle_is_never_grounded() -> None:
    assert not contains_normalized("任意句子", "   ")


def test_parse_annotated_utterance() -> None:
    parsed = parse_annotated_utterance("[date : 禮拜五] [time : 早上九點] 叫醒我")
    assert normalize_text(parsed.utterance) == normalize_text("禮拜五早上九點叫醒我")
    assert parsed.slots == (("date", "禮拜五"), ("time", "早上九點"))


def test_parse_rejects_unparsed_bracket() -> None:
    with pytest.raises(ValueError, match="Unparsed bracket"):
        parse_annotated_utterance("幫我播放 [artist 周杰倫]")
