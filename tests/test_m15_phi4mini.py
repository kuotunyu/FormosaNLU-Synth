from __future__ import annotations

from scripts.m15_phi4mini import (
    EXECUTE_CONFIRMATION,
    SMOKE_CONFIRMATION,
    _validate_smoke_payload,
)


def test_m15_confirmation_tokens_are_distinct() -> None:
    assert SMOKE_CONFIRMATION == "M15-PHI4MINI-SMOKE-4090"
    assert EXECUTE_CONFIRMATION == "M15-PHI4MINI-6RUNS-4090"
    assert SMOKE_CONFIRMATION != EXECUTE_CONFIRMATION


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
