from __future__ import annotations

from scripts.m15_phi4mini import (
    EXECUTE_CONFIRMATION,
    QUALIFY_CONFIRMATION,
    SMOKE_CONFIRMATION,
    _prediction_structure,
    _validate_qualification_payload,
    _validate_smoke_payload,
)


def test_m15_confirmation_tokens_are_distinct() -> None:
    assert SMOKE_CONFIRMATION == "M15-PHI4MINI-SMOKE-4090"
    assert QUALIFY_CONFIRMATION == "M15-SMOKE-AMENDMENT-STRUCTURAL-V2"
    assert EXECUTE_CONFIRMATION == "M15-PHI4MINI-6RUNS-4090"
    assert SMOKE_CONFIRMATION != EXECUTE_CONFIRMATION
    assert QUALIFY_CONFIRMATION != EXECUTE_CONFIRMATION


def test_m15_smoke_gate_requires_resume_eval_and_vram_headroom() -> None:
    payload = {
        "final_global_step": 2,
        "evaluation_completed": 32,
        "json_valid_rate": 0.75,
        "peak_gpu_reserved_mib": 12_000,
    }
    assert _validate_smoke_payload(payload)[0]
    payload["json_valid_rate"] = 0.0
    assert not _validate_smoke_payload(payload)[0]
    payload["json_valid_rate"] = 0.75
    payload["peak_gpu_reserved_mib"] = 25_000
    assert not _validate_smoke_payload(payload)[0]


def test_prediction_structure_separates_syntax_from_catalog_quality(tmp_path) -> None:
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(
        "\n".join(
            [
                '{"raw_prediction":"{\\"intent\\":\\"free label\\",\\"slots\\":[]}"}',
                '{"raw_prediction":"{\\"intent\\":\\"other\\",\\"slots\\":[\\"bad\\"]}"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert _prediction_structure(predictions) == {
        "rows": 2,
        "json_syntax_valid": 2,
        "json_object": 2,
        "intent_is_string": 2,
        "slots_is_list": 2,
        "slot_object_list": 1,
    }


def test_amended_smoke_gate_is_infrastructure_only() -> None:
    payload = {
        "protocol_id": "m15.smoke.infrastructure.v2",
        "status": "passed",
        "original_gate": {"status": "failed"},
        "formal_experiment_contract_unchanged": True,
        "infrastructure": {
            "first_checkpoint": "checkpoint-1",
            "resumed_from": "runs/smoke/checkpoint-1",
            "final_checkpoint": "checkpoint-2",
            "final_global_step": 2,
            "evaluation_completed": 32,
        },
        "peak_gpu_reserved_mib": 6_674,
        "structure": {
            "rows": 32,
            "json_syntax_valid": 32,
            "json_object": 32,
            "intent_is_string": 32,
            "slots_is_list": 32,
            "slot_object_list": 27,
        },
    }
    assert _validate_qualification_payload(payload)[0]
    payload["structure"]["json_syntax_valid"] = 31
    assert not _validate_qualification_payload(payload)[0]
