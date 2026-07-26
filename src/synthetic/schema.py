"""Canonical schemas for generated FormosaNLU examples."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.synthetic.labels import INTENT_SET, INTENTS, SLOT_TYPE_SET, SLOT_TYPES

RecipeName = Literal[
    "paraphrase",
    "slot_substitution",
    "noise_codeswitch",
    "hard_negative",
]
StyleName = Literal["massive_like", "tw_colloquial"]


class Slot(BaseModel):
    """One slot label whose literal value must be grounded in the utterance."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: str = Field(min_length=1, json_schema_extra={"enum": list(SLOT_TYPES)})
    value: str = Field(min_length=1)

    @field_validator("type")
    @classmethod
    def known_slot_type(cls, value: str) -> str:
        if value not in SLOT_TYPE_SET:
            raise ValueError(f"unknown slot type: {value}")
        return value


class CandidateOutput(BaseModel):
    """Schema sent to Ollama; provenance is attached locally, never invented by the LLM."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    utt: str = Field(min_length=1)
    intent: str = Field(min_length=1, json_schema_extra={"enum": list(INTENTS)})
    slots: list[Slot]

    @field_validator("intent")
    @classmethod
    def known_intent(cls, value: str) -> str:
        if value not in INTENT_SET:
            raise ValueError(f"unknown intent: {value}")
        return value


class GenerationParams(BaseModel):
    """Generation parameters needed to reproduce one request."""

    model_config = ConfigDict(extra="forbid")

    temperature: float = Field(ge=0, le=2)
    top_p: float = Field(gt=0, le=1)
    seed: int
    context_length: int = Field(gt=0)


class Provenance(BaseModel):
    """Complete, machine-checkable origin and filtering trace."""

    model_config = ConfigDict(extra="forbid")

    recipe: RecipeName
    model: str = Field(min_length=1)
    model_digest: str = Field(min_length=1)
    prompt_version: str = Field(pattern=r"^[a-z_]+\.v[1-9][0-9]*$")
    seed_sample_id: str | list[str]
    gen_params: GenerationParams
    filter_score: dict[str, float]
    filter_stage_passed: str | None
    reject_reason: str | None
    generated_at: datetime
    pair_id: str | None = None

    @model_validator(mode="after")
    def hard_negative_has_pair(self) -> Provenance:
        if self.recipe == "hard_negative":
            if not isinstance(self.seed_sample_id, list) or len(self.seed_sample_id) != 2:
                raise ValueError("hard_negative requires exactly two seed sample ids")
            if not self.pair_id:
                raise ValueError("hard_negative requires pair_id")
        return self


class SyntheticSample(CandidateOutput):
    """A generated example with stable identity and complete provenance."""

    id: str = Field(pattern=r"^syn_[0-9a-f]{20}$")
    style: StyleName
    provenance: Provenance


def content_address(
    candidate: CandidateOutput,
    *,
    style: StyleName,
    recipe: RecipeName,
    seed_sample_id: str | list[str],
    request_seed: int,
) -> str:
    """Return a stable id without timestamps or machine-specific paths."""
    payload = {
        "candidate": candidate.model_dump(mode="json"),
        "style": style,
        "recipe": recipe,
        "seed_sample_id": seed_sample_id,
        "request_seed": request_seed,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "syn_" + hashlib.sha256(encoded).hexdigest()[:20]
