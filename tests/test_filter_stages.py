from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.filtering.stages import (
    check_groundedness,
    check_locale,
    run_cheap_filters,
)
from src.synthetic.schema import SyntheticSample


def _sample(
    utt: str,
    *,
    intent: str = "alarm_set",
    slots: list[dict[str, str]] | None = None,
    recipe: str = "paraphrase",
) -> dict[str, Any]:
    return {
        "id": "syn_0123456789abcdefabcd",
        "utt": utt,
        "intent": intent,
        "slots": slots or [],
        "style": "tw_colloquial" if recipe == "noise_codeswitch" else "massive_like",
        "provenance": {
            "recipe": recipe,
            "model": "qwen3.6:27b",
            "model_digest": "sha256:test",
            "prompt_version": f"{recipe}.v1",
            "seed_sample_id": (["anchor", "target"] if recipe == "hard_negative" else "seed"),
            "gen_params": {
                "temperature": 0.2,
                "top_p": 0.9,
                "seed": 42,
                "context_length": 4096,
            },
            "filter_score": {},
            "filter_stage_passed": None,
            "reject_reason": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pair_id": "pair_test" if recipe == "hard_negative" else None,
        },
    }


def test_f1_schema_pass_and_fail() -> None:
    passed = run_cheap_filters({"sample": _sample("設定鬧鐘")})
    assert passed.reject_reason is None
    failed = run_cheap_filters({"sample": None})
    assert failed.reject_reason == "F1_SCHEMA_MISSING_SAMPLE"


def test_f2_unknown_intent_and_slot_are_classified_as_labels() -> None:
    unknown_intent = _sample("測試", intent="not_real")
    assert run_cheap_filters({"sample": unknown_intent}).reject_reason == "F2_LABEL_UNKNOWN_INTENT"
    unknown_slot = _sample(
        "設定七點",
        slots=[{"type": "not_real", "value": "七點"}],
    )
    assert run_cheap_filters({"sample": unknown_slot}).reject_reason == "F2_LABEL_UNKNOWN_SLOT"


def test_f2_recomputes_generation_plan_contract() -> None:
    record = {
        "sample": _sample(
            "設定早上七點的鬧鐘",
            slots=[{"type": "time", "value": "早上七點"}],
        ),
        "expected": {
            "intent": "alarm_set",
            "slots": [{"type": "time", "value": "晚上九點"}],
        },
    }
    assert run_cheap_filters(record).reject_reason == "F2_LABEL_CONTRACT_SLOTS"


def test_f3_groundedness_pass_fail_and_overlap() -> None:
    grounded = SyntheticSample.model_validate(
        _sample(
            "幫我設定早上七點的鬧鐘",
            slots=[{"type": "time", "value": "早上七點"}],
        )
    )
    assert check_groundedness(grounded).passed

    ungrounded = SyntheticSample.model_validate(
        _sample(
            "幫我設定鬧鐘",
            slots=[{"type": "time", "value": "早上七點"}],
        )
    )
    assert check_groundedness(ungrounded).reject_reason

    overlapping = SyntheticSample.model_validate(
        _sample(
            "導航到台北",
            intent="transport_query",
            slots=[
                {"type": "place_name", "value": "台北"},
                {"type": "business_name", "value": "北"},
            ],
        )
    )
    assert check_groundedness(overlapping).reject_reason == "F3_UNGROUNDED_OR_OVERLAPPING_SLOT"


def test_f4_locale_pass_and_fail_cases() -> None:
    assert check_locale(SyntheticSample.model_validate(_sample("幫我設定鬧鐘"))).passed
    assert (
        check_locale(SyntheticSample.model_validate(_sample("帮我设置闹钟"))).reject_reason
        == "F4_LOCALE_SIMPLIFIED"
    )
    assert (
        check_locale(SyntheticSample.model_validate(_sample("播放視頻"))).reject_reason
        == "F4_LOCALE_MAINLAND_TERM"
    )
    code_switch = SyntheticSample.model_validate(
        _sample("幫我 set 一個鬧鐘", recipe="noise_codeswitch")
    )
    assert check_locale(code_switch).passed
