from __future__ import annotations

import pytest

from src.evaluation.metrics import (
    aggregate_metrics,
    conditional_valid_diagnostics,
    diagnostic_counts,
    per_intent_accuracy,
)
from src.evaluation.parse import parse_prediction


def test_strict_parse_accepts_json_and_rejects_fences_or_unknown_label() -> None:
    parsed, error = parse_prediction('{"intent":"general_greet","slots":[]}')
    assert parsed is not None and error is None
    assert parse_prediction('```json\n{"intent":"general_greet","slots":[]}\n```')[0] is None
    assert parse_prediction('{"intent":"made_up","slots":[]}')[0] is None


def test_metrics_keep_json_invalid_in_denominator() -> None:
    expected = [
        {
            "intent": "alarm_set",
            "slots": [{"type": "time", "value": "早上七點"}],
        },
        {"intent": "general_greet", "slots": []},
    ]
    predictions = [
        '{"intent":"alarm_set","slots":[{"type":"time","value":"早上七點"}]}',
        "not json",
    ]
    metrics = aggregate_metrics(predictions, expected)
    assert metrics["samples"] == 2
    assert metrics["json_valid_rate"] == pytest.approx(0.5)
    assert metrics["intent_accuracy"] == pytest.approx(0.5)
    assert metrics["exact_match"] == pytest.approx(0.5)
    assert metrics["slot_micro_f1"] == pytest.approx(1.0)
    assert metrics["intent_macro_f1"] == pytest.approx(1 / 60)


def test_diagnostics_do_not_repair_invalid_predictions() -> None:
    predictions = [
        '{"intent":"general_greet","slots":[]}',
        "not json",
        '{"intent":"made_up","slots":[]}',
        '{"intent":"general_greet","slots":[{"slot":"person","value":"小明"}]}',
    ]
    assert diagnostic_counts(predictions) == {
        "json_decode_error": 1,
        "schema_validation_error": 1,
        "unknown_intent": 1,
        "valid": 1,
    }
    per_intent = per_intent_accuracy(
        predictions[:2],
        [
            {"intent": "general_greet", "slots": []},
            {"intent": "alarm_set", "slots": []},
        ],
    )
    assert per_intent["general_greet"]["accuracy"] == 1.0
    assert per_intent["alarm_set"]["accuracy"] == 0.0
    assert conditional_valid_diagnostics(
        predictions[:2],
        [
            {"intent": "general_greet", "slots": []},
            {"intent": "alarm_set", "slots": []},
        ],
    ) == {
        "valid_rows": 1,
        "intent_correct": 1,
        "intent_accuracy": 1.0,
    }
