from __future__ import annotations

import json

import pytest

from scripts.analyse_intent_confusion import (
    analyse,
    confusion_flow,
    load_predictions,
    per_intent_accuracy,
)


def _write(path, rows) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for index, (row_id, gold, predicted, utt) in enumerate(rows):
            raw = "not json" if predicted is None else json.dumps({"intent": predicted})
            handle.write(
                json.dumps(
                    {
                        "generation_index": index,
                        "expected": {"id": row_id, "intent": gold, "utt": utt},
                        "raw_prediction": raw,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def test_unparseable_prediction_counts_as_wrong_not_skipped(tmp_path) -> None:
    """Dropping unparseable rows would flatter a model that emits garbage."""
    path = tmp_path / "p.jsonl"
    _write(path, [("1", "alarm_set", "alarm_set", "a"), ("2", "alarm_set", None, "b")])

    rows = load_predictions(path)
    assert rows["2"][1] is None
    assert per_intent_accuracy(rows)["alarm_set"] == (1, 2)


def test_single_seed_extreme_is_reported_alongside_its_spread() -> None:
    """A +50 point swing on one seed and ~0 on others must not read as +50."""
    predictions = {
        "real_only": {
            42: {"1": ("qa_factoid", "general_quirky", "u")},
            43: {"1": ("qa_factoid", "qa_factoid", "u")},
        },
        "real_syn_filtered": {
            42: {"1": ("qa_factoid", "qa_factoid", "u")},
            43: {"1": ("qa_factoid", "qa_factoid", "u")},
        },
    }

    report = analyse(predictions, seeds=[42, 43])
    entry = report["per_intent"]["qa_factoid"]

    assert entry["real_only"]["per_seed"] == pytest.approx([0.0, 100.0])
    assert entry["paired_delta"]["per_seed"] == pytest.approx([100.0, 0.0])
    assert entry["paired_delta"]["mean"] == pytest.approx(50.0)
    # The spread is what stops the 100 from being quoted as the effect.
    assert entry["real_only"]["range"] == pytest.approx(100.0)


def test_ranking_surfaces_the_least_stable_baseline_intent() -> None:
    predictions = {
        "real_only": {
            42: {
                "1": ("steady", "steady", "u"),
                "2": ("swingy", "other", "u"),
            },
            43: {
                "1": ("steady", "steady", "u"),
                "2": ("swingy", "swingy", "u"),
            },
        },
        "real_syn_filtered": {
            42: {
                "1": ("steady", "steady", "u"),
                "2": ("swingy", "swingy", "u"),
            },
            43: {
                "1": ("steady", "steady", "u"),
                "2": ("swingy", "swingy", "u"),
            },
        },
    }

    report = analyse(predictions, seeds=[42, 43])
    assert report["most_unstable_baseline_intents"][0] == "swingy"


def test_confusion_flow_reports_per_seed_destinations() -> None:
    predictions = {
        "real_only": {
            42: {"1": ("general_quirky", "qa_factoid", "u")},
        },
        "real_syn_filtered": {
            42: {"1": ("general_quirky", "general_quirky", "u")},
        },
    }

    flow = confusion_flow(predictions, gold="general_quirky", seeds=[42])
    assert flow["real_only"][42] == {"qa_factoid": 1}
    assert flow["real_syn_filtered"][42] == {"general_quirky": 1}
