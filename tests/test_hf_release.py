from __future__ import annotations

import pytest

from scripts.hf_release import (
    BASE_MODEL_ID,
    assert_safe_text,
    flatten_release_row,
    sanitize_adapter_config,
)


def test_flatten_release_row_keeps_public_training_and_provenance_fields() -> None:
    payload = {
        "sample": {
            "id": "syn_123",
            "utt": "明天提醒我開會",
            "intent": "calendar_set",
            "slots": [{"type": "date", "value": "明天"}],
            "style": "tw_colloquial",
            "provenance": {
                "recipe": "slot_substitution",
                "model": "qwen3.6:27b",
                "model_digest": "abc",
                "prompt_version": "slot_substitution.v1",
                "seed_sample_id": "42",
                "gen_params": {"temperature": 0.2},
                "filter_score": {"f6_max_eval": 0.8},
            },
        }
    }

    row = flatten_release_row(payload)

    assert row["id"] == "syn_123"
    assert row["utt"] == "明天提醒我開會"
    assert row["slots"] == [{"type": "date", "value": "明天"}]
    assert row["teacher_model"] == "qwen3.6:27b"
    assert "metrics" not in row
    assert "raw_content" not in row


def test_sanitize_adapter_config_removes_machine_local_base_path() -> None:
    original = {
        "base_model_name_or_path": r"C:\Users\example\model",
        "peft_type": "LORA",
    }

    sanitized = sanitize_adapter_config(original)

    assert sanitized["base_model_name_or_path"] == BASE_MODEL_ID
    assert sanitized["peft_type"] == "LORA"
    assert original["base_model_name_or_path"] == r"C:\Users\example\model"


@pytest.mark.parametrize(
    "unsafe",
    [
        "C:" + r"\Users\3Hml\Desktop\model",
        "hf_" + "a" * 30,
        "github_pat_" + "b" * 30,
        "[More Information Needed]",
    ],
)
def test_safe_text_rejects_paths_tokens_and_placeholders(unsafe: str) -> None:
    with pytest.raises(ValueError):
        assert_safe_text(unsafe, label="fixture")


def test_safe_text_accepts_public_model_and_repository_ids() -> None:
    assert_safe_text(
        "google/gemma-4-E4B-it steven0226/formosa-nlu-synth-v1",
        label="fixture",
    )
