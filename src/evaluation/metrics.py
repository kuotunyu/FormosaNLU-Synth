"""Frozen FormosaNLU metrics; JSON-invalid rows remain in every denominator."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from src.data.normalize import normalize_text
from src.evaluation.parse import parse_prediction
from src.synthetic.labels import INTENTS


@dataclass(frozen=True)
class ScoredRow:
    json_valid: bool
    intent_correct: bool
    expected_slots: Counter[tuple[str, str]]
    predicted_slots: Counter[tuple[str, str]]
    exact_match: bool


def _slot_counter(slots: list[dict[str, str]] | list[Any]) -> Counter[tuple[str, str]]:
    return Counter(
        (
            slot["type"] if isinstance(slot, dict) else slot.type,
            normalize_text(slot["value"] if isinstance(slot, dict) else slot.value),
        )
        for slot in slots
    )


def score_row(raw_prediction: str, expected: dict[str, Any]) -> ScoredRow:
    prediction, _ = parse_prediction(raw_prediction)
    expected_slots = _slot_counter(expected["slots"])
    if prediction is None:
        return ScoredRow(
            json_valid=False,
            intent_correct=False,
            expected_slots=expected_slots,
            predicted_slots=Counter(),
            exact_match=False,
        )
    predicted_slots = _slot_counter(prediction.slots)
    intent_correct = prediction.intent == expected["intent"]
    return ScoredRow(
        json_valid=True,
        intent_correct=intent_correct,
        expected_slots=expected_slots,
        predicted_slots=predicted_slots,
        exact_match=intent_correct and predicted_slots == expected_slots,
    )


def aggregate_metrics(
    raw_predictions: list[str],
    expected_rows: list[dict[str, Any]],
) -> dict[str, float]:
    if len(raw_predictions) != len(expected_rows) or not raw_predictions:
        raise ValueError("Predictions and expected rows must have equal non-zero length")
    scored = [
        score_row(raw, expected)
        for raw, expected in zip(raw_predictions, expected_rows, strict=True)
    ]
    total = len(scored)
    per_intent_correct: Counter[str] = Counter()
    per_intent_total: Counter[str] = Counter()
    true_positive = false_positive = false_negative = 0
    for row, expected in zip(scored, expected_rows, strict=True):
        intent = expected["intent"]
        per_intent_total[intent] += 1
        per_intent_correct[intent] += int(row.intent_correct)
        true_positive += sum((row.expected_slots & row.predicted_slots).values())
        false_positive += sum((row.predicted_slots - row.expected_slots).values())
        false_negative += sum((row.expected_slots - row.predicted_slots).values())

    # For single-label intent classification, per-class F1 requires predicted
    # intent counts. Reparse only valid rows; invalid contributes no prediction.
    predicted_by_intent: Counter[str] = Counter()
    tp_by_intent: Counter[str] = Counter()
    for raw, expected in zip(raw_predictions, expected_rows, strict=True):
        prediction, _ = parse_prediction(raw)
        if prediction is not None:
            predicted_by_intent[prediction.intent] += 1
            if prediction.intent == expected["intent"]:
                tp_by_intent[prediction.intent] += 1
    f1_values = []
    for intent in INTENTS:
        tp = tp_by_intent[intent]
        fp = predicted_by_intent[intent] - tp
        fn = per_intent_total[intent] - tp
        denominator = 2 * tp + fp + fn
        f1_values.append(2 * tp / denominator if denominator else 0.0)

    slot_denominator = 2 * true_positive + false_positive + false_negative
    return {
        "samples": float(total),
        "json_valid_rate": sum(row.json_valid for row in scored) / total,
        "intent_accuracy": sum(row.intent_correct for row in scored) / total,
        "intent_macro_f1": sum(f1_values) / len(INTENTS),
        "slot_micro_f1": (2 * true_positive / slot_denominator if slot_denominator else 1.0),
        "exact_match": sum(row.exact_match for row in scored) / total,
    }
