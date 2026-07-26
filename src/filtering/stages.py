"""Cheap F1-F4 filters shared by pilot and full generation."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from opencc import OpenCC
from pydantic import ValidationError

from src.data.normalize import normalize_text
from src.synthetic.labels import INTENT_SET, SLOT_TYPE_SET
from src.synthetic.schema import SyntheticSample

_S2T = OpenCC("s2t")
_MAINLAND_TERMS = {
    "視頻": "影片",
    "軟件": "軟體",
    "硬件": "硬體",
    "信息": "訊息",
    "網絡": "網路",
    "出租車": "計程車",
    "公交": "公車",
    "地鐵": "捷運",
    "文件夾": "資料夾",
    "默認": "預設",
    "打印": "列印",
}
_UNEXPECTED_SCRIPT_RE = re.compile(r"[\u3040-\u30ff\uac00-\ud7af\u0400-\u04ff]")


@dataclass(frozen=True)
class StageResult:
    """One filter stage outcome."""

    passed: bool
    stage: str
    reject_reason: str | None = None
    scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class CheapFilterResult:
    """Parsed sample and the first F1-F4 rejection, if any."""

    sample: SyntheticSample | None
    passed_stage: str | None
    reject_reason: str | None
    scores: dict[str, float]
    validation_error: str | None = None


def check_schema(record: dict[str, Any]) -> tuple[SyntheticSample | None, StageResult, str | None]:
    sample_data = record.get("sample")
    if not isinstance(sample_data, dict):
        return None, StageResult(False, "F1", "F1_SCHEMA_MISSING_SAMPLE"), None
    try:
        sample = SyntheticSample.model_validate(sample_data)
    except ValidationError as exc:
        errors = exc.errors()
        label_errors = [
            error
            for error in errors
            if error["loc"]
            and error["loc"][-1] in {"intent", "type"}
            and "unknown" in error["msg"]
        ]
        if label_errors and len(label_errors) == len(errors):
            reason = (
                "F2_LABEL_UNKNOWN_INTENT"
                if any(error["loc"][-1] == "intent" for error in label_errors)
                else "F2_LABEL_UNKNOWN_SLOT"
            )
            return None, StageResult(False, "F2", reason), str(exc)
        return None, StageResult(False, "F1", "F1_SCHEMA_INVALID"), str(exc)
    return sample, StageResult(True, "F1"), None


def check_labels(sample: SyntheticSample) -> StageResult:
    if sample.intent not in INTENT_SET:
        return StageResult(False, "F2", "F2_LABEL_UNKNOWN_INTENT")
    if any(slot.type not in SLOT_TYPE_SET for slot in sample.slots):
        return StageResult(False, "F2", "F2_LABEL_UNKNOWN_SLOT")
    return StageResult(True, "F2")


def check_expected_contract(
    record: dict[str, Any],
    sample: SyntheticSample,
) -> StageResult:
    """Verify labels still match the code-authored generation plan, when present."""
    expected = record.get("expected")
    if expected is None:
        return StageResult(True, "F2")
    if not isinstance(expected, dict):
        return StageResult(False, "F1", "F1_SCHEMA_INVALID_EXPECTED")
    if sample.intent != expected.get("intent"):
        return StageResult(False, "F2", "F2_LABEL_CONTRACT_INTENT")
    expected_slots = expected.get("slots")
    if not isinstance(expected_slots, list):
        return StageResult(False, "F1", "F1_SCHEMA_INVALID_EXPECTED")
    expected_pairs = sorted(
        (slot.get("type"), slot.get("value"))
        for slot in expected_slots
        if isinstance(slot, dict)
    )
    actual_pairs = sorted((slot.type, slot.value) for slot in sample.slots)
    if len(expected_pairs) != len(expected_slots) or actual_pairs != expected_pairs:
        return StageResult(False, "F2", "F2_LABEL_CONTRACT_SLOTS")
    return StageResult(True, "F2")


def _assign_non_overlapping_spans(
    utterance: str,
    values: list[str],
) -> list[tuple[int, int]] | None:
    normalized_utt = normalize_text(utterance)
    occupied: list[tuple[int, int]] = []
    for value in sorted(values, key=lambda item: len(normalize_text(item)), reverse=True):
        normalized_value = normalize_text(value)
        if not normalized_value:
            return None
        start = 0
        assigned: tuple[int, int] | None = None
        while True:
            found = normalized_utt.find(normalized_value, start)
            if found < 0:
                break
            candidate = (found, found + len(normalized_value))
            if all(candidate[1] <= span[0] or candidate[0] >= span[1] for span in occupied):
                assigned = candidate
                break
            start = found + 1
        if assigned is None:
            return None
        occupied.append(assigned)
    return occupied


def check_groundedness(sample: SyntheticSample) -> StageResult:
    spans = _assign_non_overlapping_spans(
        sample.utt,
        [slot.value for slot in sample.slots],
    )
    if spans is None:
        return StageResult(False, "F3", "F3_UNGROUNDED_OR_OVERLAPPING_SLOT")
    return StageResult(
        True,
        "F3",
        scores={"slot_span_count": float(len(spans))},
    )


def _letter_ratios(text: str) -> tuple[float, float]:
    letters = [char for char in text if unicodedata.category(char).startswith("L")]
    if not letters:
        return 0.0, 0.0
    latin = sum("LATIN" in unicodedata.name(char, "") for char in letters)
    han = sum("\u3400" <= char <= "\u9fff" for char in letters)
    return latin / len(letters), han / len(letters)


def check_locale(sample: SyntheticSample) -> StageResult:
    utterance = unicodedata.normalize("NFKC", sample.utt)
    converted = _S2T.convert(utterance)
    changed_han = sum(
        before != after
        for before, after in zip(utterance, converted, strict=False)
        if "\u3400" <= before <= "\u9fff"
    )
    if changed_han:
        return StageResult(
            False,
            "F4",
            "F4_LOCALE_SIMPLIFIED",
            {"simplified_char_count": float(changed_han)},
        )
    if _UNEXPECTED_SCRIPT_RE.search(utterance):
        return StageResult(False, "F4", "F4_LOCALE_UNEXPECTED_SCRIPT")
    if any(term in utterance for term in _MAINLAND_TERMS):
        return StageResult(False, "F4", "F4_LOCALE_MAINLAND_TERM")

    latin_ratio, han_ratio = _letter_ratios(utterance)
    latin_limit = 0.55 if sample.provenance.recipe == "noise_codeswitch" else 0.30
    if latin_ratio > latin_limit or (han_ratio == 0 and latin_ratio > 0):
        return StageResult(
            False,
            "F4",
            "F4_LOCALE_LANGUAGE_RATIO",
            {"latin_ratio": latin_ratio, "han_ratio": han_ratio},
        )
    return StageResult(
        True,
        "F4",
        scores={"latin_ratio": latin_ratio, "han_ratio": han_ratio},
    )


def run_cheap_filters(record: dict[str, Any]) -> CheapFilterResult:
    sample, schema_result, validation_error = check_schema(record)
    scores = dict(schema_result.scores)
    if not schema_result.passed:
        return CheapFilterResult(
            sample=None,
            passed_stage=None,
            reject_reason=schema_result.reject_reason,
            scores=scores,
            validation_error=validation_error,
        )
    assert sample is not None
    passed_stage = "F1"
    checks = (
        check_labels(sample),
        check_expected_contract(record, sample),
        check_groundedness(sample),
        check_locale(sample),
    )
    for result in checks:
        scores.update(result.scores)
        if not result.passed:
            return CheapFilterResult(
                sample=sample,
                passed_stage=passed_stage,
                reject_reason=result.reject_reason,
                scores=scores,
            )
        passed_stage = result.stage
    return CheapFilterResult(
        sample=sample,
        passed_stage=passed_stage,
        reject_reason=None,
        scores=scores,
    )
