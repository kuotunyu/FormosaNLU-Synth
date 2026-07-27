from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.synthetic.labels import INTENTS, LABELS_SHA256, SLOT_TYPES, verify_manifest_labels
from src.synthetic.schema import (
    CandidateOutput,
    GenerationParams,
    Provenance,
    Slot,
    SyntheticSample,
    content_address,
)


def test_frozen_labels_match_manifest() -> None:
    assert len(INTENTS) == 60
    assert len(SLOT_TYPES) == 55
    assert verify_manifest_labels() == LABELS_SHA256


def test_candidate_rejects_unknown_labels() -> None:
    with pytest.raises(ValidationError):
        CandidateOutput(utt="測試", intent="not_an_intent", slots=[])
    with pytest.raises(ValidationError):
        Slot(type="not_a_slot", value="測試")


def test_content_address_is_stable_and_provenance_is_complete() -> None:
    candidate = CandidateOutput(
        utt="幫我設定早上七點的鬧鐘",
        intent="alarm_set",
        slots=[Slot(type="time", value="早上七點")],
    )
    sample_id = content_address(
        candidate,
        style="tw_colloquial",
        recipe="paraphrase",
        seed_sample_id="seed-1",
        request_seed=42,
    )
    assert sample_id == content_address(
        candidate,
        style="tw_colloquial",
        recipe="paraphrase",
        seed_sample_id="seed-1",
        request_seed=42,
    )
    SyntheticSample(
        id=sample_id,
        **candidate.model_dump(),
        style="tw_colloquial",
        provenance=Provenance(
            recipe="paraphrase",
            model="qwen3.6:27b",
            model_digest="sha256:test",
            prompt_version="paraphrase.v1",
            seed_sample_id="seed-1",
            gen_params=GenerationParams(
                temperature=0.2,
                top_p=0.9,
                seed=42,
                context_length=4096,
            ),
            filter_score={},
            filter_stage_passed=None,
            reject_reason=None,
            generated_at=datetime.now(timezone.utc),
        ),
    )


def test_hard_negative_requires_two_seeds_and_pair_id() -> None:
    common = {
        "recipe": "hard_negative",
        "model": "qwen3.6:27b",
        "model_digest": "sha256:test",
        "prompt_version": "hard_negative.v1",
        "gen_params": {
            "temperature": 0.2,
            "top_p": 0.9,
            "seed": 42,
            "context_length": 4096,
        },
        "filter_score": {},
        "filter_stage_passed": None,
        "reject_reason": None,
        "generated_at": datetime.now(timezone.utc),
    }
    with pytest.raises(ValidationError):
        Provenance(seed_sample_id="only-one", pair_id=None, **common)
    Provenance(seed_sample_id=["anchor", "target"], pair_id="pair_test", **common)
