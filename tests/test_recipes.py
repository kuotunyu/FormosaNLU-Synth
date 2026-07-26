from __future__ import annotations

import pytest

from src.synthetic.recipes import (
    build_hard_negative,
    build_noise_codeswitch,
    build_paraphrase,
    build_slot_substitution,
)
from src.synthetic.recipes.slot_substitution import substitute_seed

ALARM_SEED = {
    "id": "alarm-1",
    "utt": "幫我設定早上七點的鬧鐘",
    "intent": "alarm_set",
    "slots": [{"type": "time", "value": "早上七點"}],
}
QUERY_SEED = {
    "id": "alarm-2",
    "utt": "我有設定什麼鬧鐘",
    "intent": "alarm_query",
    "slots": [],
}


def test_paraphrase_prompt_is_versioned_and_complete() -> None:
    plan = build_paraphrase(ALARM_SEED, "massive_like")
    assert plan.prompt_version == "paraphrase.v2"
    assert "{{" not in plan.user_prompt
    assert plan.expected_slots == (("time", "早上七點"),)


def test_slot_substitution_is_procedural() -> None:
    draft = substitute_seed(ALARM_SEED, ("time", "早上七點", "晚上九點"))
    assert draft["utt"] == "幫我設定晚上九點的鬧鐘"
    assert draft["slots"] == [{"type": "time", "value": "晚上九點"}]
    plan = build_slot_substitution(
        ALARM_SEED,
        "tw_colloquial",
        ("time", "早上七點", "晚上九點"),
    )
    assert "晚上九點" in plan.user_prompt
    assert "早上七點" not in plan.user_prompt


def test_slot_substitution_rejects_ungrounded_source() -> None:
    with pytest.raises(ValueError):
        substitute_seed(ALARM_SEED, ("time", "七點", "九點"))


def test_noise_recipe_is_always_colloquial() -> None:
    plan = build_noise_codeswitch(ALARM_SEED)
    assert plan.style == "tw_colloquial"
    assert plan.prompt_version == "noise_codeswitch.v2"


def test_hard_negative_uses_target_labels_and_two_seed_ids() -> None:
    plan = build_hard_negative(QUERY_SEED, ALARM_SEED, "massive_like")
    assert plan.expected_intent == "alarm_set"
    assert plan.expected_slots == (("time", "早上七點"),)
    assert plan.seed_sample_id == ["alarm-2", "alarm-1"]
    assert plan.pair_id and plan.pair_id.startswith("pair_")
