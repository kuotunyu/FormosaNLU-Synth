from __future__ import annotations

from src.synthetic.labels import INTENTS, SLOT_TYPES
from src.training.prompt_template import (
    TEMPLATE_VERSION,
    build_prompt_completion,
    build_prompt_messages,
)


def test_zero_shot_includes_full_label_catalog_but_training_does_not() -> None:
    zero_shot = build_prompt_messages("幫我設定鬧鐘", zero_shot=True)
    training = build_prompt_messages("幫我設定鬧鐘", zero_shot=False)
    zero_text = zero_shot[-1]["content"]
    train_text = training[-1]["content"]
    assert all(intent in zero_text for intent in INTENTS)
    assert all(slot_type in zero_text for slot_type in SLOT_TYPES)
    assert "alarm_set" not in train_text
    assert TEMPLATE_VERSION == "formosanlu_nlu.v1"


def test_prompt_completion_target_is_compact_json() -> None:
    row = build_prompt_completion(
        {
            "utt": "幫我設定早上七點的鬧鐘",
            "intent": "alarm_set",
            "slots": [{"type": "time", "value": "早上七點"}],
        }
    )
    assert row["prompt"][0]["role"] == "system"
    assert row["completion"] == [
        {
            "role": "assistant",
            "content": ('{"intent":"alarm_set","slots":[{"type":"time","value":"早上七點"}]}'),
        }
    ]
