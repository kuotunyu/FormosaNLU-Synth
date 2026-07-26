"""Strict, unconstrained parsing of NLU model output."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from src.synthetic.labels import INTENT_SET, SLOT_TYPE_SET
from src.synthetic.schema import Slot


class NluOutput(BaseModel):
    """The model-visible output contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    intent: str
    slots: list[Slot]

    @field_validator("intent")
    @classmethod
    def known_intent(cls, value: str) -> str:
        if value not in INTENT_SET:
            raise ValueError(f"unknown intent: {value}")
        return value

    @field_validator("slots")
    @classmethod
    def known_slots(cls, values: list[Slot]) -> list[Slot]:
        if any(slot.type not in SLOT_TYPE_SET for slot in values):
            raise ValueError("unknown slot type")
        return values


def parse_prediction(raw: str) -> tuple[NluOutput | None, str | None]:
    """Parse one raw response; markdown fences and surrounding prose are invalid."""
    stripped = raw.strip()
    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return None, f"JSONDecodeError: {exc}"
    try:
        return NluOutput.model_validate(decoded), None
    except ValidationError as exc:
        return None, f"ValidationError: {exc}"
