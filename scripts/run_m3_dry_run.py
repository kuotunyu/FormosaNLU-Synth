"""Generate five review samples for each versioned M3 recipe."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from src.data.load_massive import DEFAULT_DATA_DIR, decode_example, load_massive_split
from src.data.normalize import contains_normalized, parse_annotated_utterance
from src.synthetic.recipes import (
    RecipePlan,
    build_hard_negative,
    build_noise_codeswitch,
    build_paraphrase,
    build_slot_substitution,
)
from src.synthetic.recipes.hard_negative import CONFUSION_PAIRS
from src.synthetic.schema import (
    CandidateOutput,
    GenerationParams,
    Provenance,
    SyntheticSample,
    content_address,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "splits" / "manifest.json"
DEFAULT_JSON = REPO_ROOT / "reports" / "m3_recipe_samples.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports" / "m3_recipe_samples.md"
DEFAULT_BASELINE = REPO_ROOT / "reports" / "m3_recipe_samples_v1.json"
OLLAMA_URL = "http://127.0.0.1:11434"


def _seed_from_example(example: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_annotated_utterance(example["annot_utt"])
    return {
        "id": example["id"],
        "utt": example["utt"],
        "intent": example["intent"],
        "slots": [
            {"type": slot_type, "value": slot_value} for slot_type, slot_value in parsed.slots
        ],
    }


def _load_seed_pool(
    manifest_path: Path,
    data_dir: Path,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = manifest["splits"]["train_20shot_by_intent"]
    selected_ids = {sample_id for intent_ids in selected.values() for sample_id in intent_ids}
    dataset = load_massive_split("train", data_dir, download=False)
    index_by_id = {sample_id: index for index, sample_id in enumerate(dataset["id"])}

    by_intent: dict[str, list[dict[str, Any]]] = {}
    flat: list[dict[str, Any]] = []
    for intent in sorted(selected):
        seeds = [
            _seed_from_example(decode_example(dataset, index_by_id[sample_id]))
            for sample_id in selected[intent]
            if sample_id in selected_ids
        ]
        by_intent[intent] = seeds
        flat.extend(seeds)
    return by_intent, flat


def _choose_substitution_plans(pool: list[dict[str, Any]]) -> list[RecipePlan]:
    value_bank: dict[str, list[str]] = {}
    for seed in pool:
        for slot in seed["slots"]:
            values = value_bank.setdefault(slot["type"], [])
            if slot["value"] not in values:
                values.append(slot["value"])

    plans: list[RecipePlan] = []
    seen_intents: set[str] = set()
    for seed in pool:
        if seed["intent"] in seen_intents:
            continue
        for slot in seed["slots"]:
            old_value = slot["value"]
            if old_value not in seed["utt"]:
                continue
            replacement = next(
                (
                    value
                    for value in value_bank[slot["type"]]
                    if value != old_value and value not in seed["utt"]
                ),
                None,
            )
            if replacement is None:
                continue
            style = "massive_like" if len(plans) % 2 == 0 else "tw_colloquial"
            plans.append(
                build_slot_substitution(
                    seed,
                    style,
                    (slot["type"], old_value, replacement),
                )
            )
            seen_intents.add(seed["intent"])
            break
        if len(plans) == 5:
            return plans
    raise RuntimeError(f"Could only build {len(plans)} slot-substitution plans")


def _build_plans(
    by_intent: dict[str, list[dict[str, Any]]],
    pool: list[dict[str, Any]],
) -> list[RecipePlan]:
    first_seeds = [by_intent[intent][0] for intent in sorted(by_intent)]
    paraphrase = [
        build_paraphrase(seed, "massive_like" if index % 2 == 0 else "tw_colloquial")
        for index, seed in enumerate(first_seeds[:5])
    ]
    substitutions = _choose_substitution_plans(pool)
    noise = [build_noise_codeswitch(seed) for seed in first_seeds[5:10]]
    hard_negatives: list[RecipePlan] = []
    for anchor_intent, target_intent in CONFUSION_PAIRS[:5]:
        style = "massive_like" if len(hard_negatives) % 2 == 0 else "tw_colloquial"
        hard_negatives.append(
            build_hard_negative(
                by_intent[anchor_intent][0],
                by_intent[target_intent][0],
                style,
            )
        )
    plans = paraphrase + substitutions + noise + hard_negatives
    if len(plans) != 20:
        raise AssertionError(f"Expected 20 plans, got {len(plans)}")
    return plans


async def _model_digest(client: httpx.AsyncClient, model: str) -> str:
    response = await client.get("/api/tags")
    response.raise_for_status()
    for entry in response.json().get("models", []):
        if entry.get("name") == model or entry.get("model") == model:
            return str(entry.get("digest", "unknown"))
    return "unknown"


def _first_reject_reason(
    candidate: CandidateOutput,
    plan: RecipePlan,
) -> str | None:
    if candidate.intent != plan.expected_intent:
        return "F2_INTENT_CONTRACT"
    actual_slots = sorted((slot.type, slot.value) for slot in candidate.slots)
    if actual_slots != sorted(plan.expected_slots):
        return "F2_SLOT_CONTRACT"
    if not all(contains_normalized(candidate.utt, slot.value) for slot in candidate.slots):
        return "F3_UNGROUNDED_SLOT"
    return None


async def _generate_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    *,
    plan: RecipePlan,
    index: int,
    model: str,
    model_digest: str,
    num_ctx: int,
    temperature: float,
    top_p: float,
) -> dict[str, Any]:
    request_seed = 43_000 + index
    async with semaphore:
        started = time.perf_counter()
        response = await client.post(
            "/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": plan.system_prompt},
                    {"role": "user", "content": plan.user_prompt},
                ],
                "stream": False,
                "think": False,
                "format": CandidateOutput.model_json_schema(),
                "options": {
                    "temperature": temperature,
                    "top_p": top_p,
                    "seed": request_seed,
                    "num_ctx": num_ctx,
                    "num_predict": 220,
                },
            },
        )
        wall_seconds = time.perf_counter() - started
    response.raise_for_status()
    envelope = response.json()
    content = envelope["message"]["content"]
    candidate: CandidateOutput | None = None
    validation_error: str | None = None
    try:
        candidate = CandidateOutput.model_validate_json(content)
    except ValidationError as exc:
        validation_error = str(exc)

    reject_reason = (
        _first_reject_reason(candidate, plan) if candidate is not None else "F1_SCHEMA_INVALID"
    )
    sample: SyntheticSample | None = None
    if candidate is not None:
        provenance = Provenance(
            recipe=plan.recipe,
            model=model,
            model_digest=model_digest,
            prompt_version=plan.prompt_version,
            seed_sample_id=plan.seed_sample_id,
            gen_params=GenerationParams(
                temperature=temperature,
                top_p=top_p,
                seed=request_seed,
                context_length=num_ctx,
            ),
            filter_score={"m3_contract_valid": 1.0 if reject_reason is None else 0.0},
            filter_stage_passed="F3" if reject_reason is None else None,
            reject_reason=reject_reason,
            generated_at=datetime.now(timezone.utc),
            pair_id=plan.pair_id,
        )
        sample = SyntheticSample(
            id=content_address(
                candidate,
                style=plan.style,
                recipe=plan.recipe,
                seed_sample_id=plan.seed_sample_id,
                request_seed=request_seed,
            ),
            **candidate.model_dump(),
            style=plan.style,
            provenance=provenance,
        )

    return {
        "recipe": plan.recipe,
        "prompt_version": plan.prompt_version,
        "style": plan.style,
        "expected_intent": plan.expected_intent,
        "expected_slots": [
            {"type": slot_type, "value": value} for slot_type, value in plan.expected_slots
        ],
        "seed_sample_id": plan.seed_sample_id,
        "pair_id": plan.pair_id,
        "sample": sample.model_dump(mode="json") if sample else None,
        "raw_content": None if sample else content,
        "json_valid": candidate is not None,
        "contract_valid": reject_reason is None,
        "reject_reason": reject_reason,
        "validation_error": validation_error,
        "wall_seconds": wall_seconds,
        "prompt_eval_count": envelope.get("prompt_eval_count", 0),
        "eval_count": envelope.get("eval_count", 0),
    }


def _escape_table(value: Any) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("|", "\\|").replace("\n", "<br>")


def _render_markdown(
    payload: dict[str, Any],
    baseline: dict[str, Any] | None = None,
) -> str:
    summary = payload["summary"]
    lines = [
        "# M3 Recipe Dry-run Samples",
        "",
        f"- Model: `{payload['model']}` (`{payload['model_digest'][:20]}…`)",
        f"- Prompt versions: {', '.join(f'`{value}`' for value in payload['prompt_versions'])}",
        f"- Samples: {summary['samples']}（每個 recipe 5 筆）",
        f"- JSON-valid: {summary['json_valid']}/{summary['samples']}",
        f"- Intent／slot／grounding contract valid: "
        f"{summary['contract_valid']}/{summary['samples']}",
        f"- Measured wall time: {summary['wall_seconds']:.2f} s",
        "",
        "> 這是 M3 的人工 review 樣本，不是 M4 pilot，也不會用來調整 M4 固定門檻。",
        "",
    ]
    if baseline is not None:
        baseline_summary = baseline["summary"]
        lines.extend(
            [
                "## Prompt iteration",
                "",
                "| Round | Versions | JSON-valid | Contract valid | Observation |",
                "|---|---|---:|---:|---|",
                f"| v1 | {' / '.join(f'`{value}`' for value in baseline['prompt_versions'])} "
                f"| {baseline_summary['json_valid']}/{baseline_summary['samples']} "
                f"| {baseline_summary['contract_valid']}/{baseline_summary['samples']} "
                "| hard-negative 三次複製 anchor labels；兩筆 noise 語句不自然 |",
                "| v2（採用） | "
                f"{' / '.join(f'`{value}`' for value in payload['prompt_versions'])} "
                f"| {summary['json_valid']}/{summary['samples']} "
                f"| **{summary['contract_valid']}/{summary['samples']}** "
                "| target-label 指令修正 hard-negative；唯一失敗是原 seed 的 "
                "`星期二的` 被改成 `星期二` |",
                "",
                "第一輪完整原始輸出保留在 `reports/m3_recipe_samples_v1.{json,md}`，沒有用第二輪",
                "覆蓋失敗證據。`slot_substitution.v1` 第一輪即為 5/5，因此沒有為了增加"
                "版本號而改動。",
                "",
            ]
        )
    for recipe in (
        "paraphrase",
        "slot_substitution",
        "noise_codeswitch",
        "hard_negative",
    ):
        lines.extend(
            [
                f"## `{recipe}`",
                "",
                "| # | style | seed | intent | slots | output | contract |",
                "|---:|---|---|---|---|---|---|",
            ]
        )
        recipe_rows = [row for row in payload["results"] if row["recipe"] == recipe]
        for index, row in enumerate(recipe_rows, start=1):
            sample = row["sample"]
            output = sample["utt"] if sample else row["raw_content"]
            intent = sample["intent"] if sample else "—"
            slots = sample["slots"] if sample else []
            status = "PASS" if row["contract_valid"] else row["reject_reason"]
            lines.append(
                f"| {index} | `{row['style']}` | "
                f"{_escape_table(row['seed_sample_id'])} | `{intent}` | "
                f"{_escape_table(slots)} | {_escape_table(output)} | `{status}` |"
            )
        lines.append("")
    lines.extend(
        [
            "## Review notes",
            "",
            "- `slot_substitution` 的新 value 由程式從同 slot type 的 frozen train pool "
            "選出，再交給 teacher 修語氣；label 不是由 teacher 猜。",
            "- `noise_codeswitch` 按設計固定為 `tw_colloquial`；其他 recipe 同時覆蓋 "
            "`massive_like` 與 `tw_colloquial`。",
            "- 原始結構化結果、tokens、每筆 provenance 與 reject reason 在 "
            "`reports/m3_recipe_samples.json`。",
            "",
        ]
    )
    return "\n".join(lines)


async def async_main(args: argparse.Namespace) -> int:
    by_intent, pool = _load_seed_pool(args.manifest, args.data_dir)
    plans = _build_plans(by_intent, pool)
    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(base_url=args.ollama_url, timeout=timeout) as client:
        digest = await _model_digest(client, args.model)
        semaphore = asyncio.Semaphore(args.concurrency)
        started = time.perf_counter()
        results = await asyncio.gather(
            *(
                _generate_one(
                    client,
                    semaphore,
                    plan=plan,
                    index=index,
                    model=args.model,
                    model_digest=digest,
                    num_ctx=args.num_ctx,
                    temperature=args.temperature,
                    top_p=args.top_p,
                )
                for index, plan in enumerate(plans)
            )
        )
        wall_seconds = time.perf_counter() - started

    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "model_digest": digest,
        "prompt_versions": sorted({plan.prompt_version for plan in plans}),
        "summary": {
            "samples": len(results),
            "json_valid": sum(row["json_valid"] for row in results),
            "contract_valid": sum(row["contract_valid"] for row in results),
            "wall_seconds": wall_seconds,
            "prompt_tokens": sum(row["prompt_eval_count"] for row in results),
            "output_tokens": sum(row["eval_count"] for row in results),
        },
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    baseline = (
        json.loads(args.baseline_json.read_text(encoding="utf-8"))
        if args.baseline_json.exists()
        else None
    )
    args.output_markdown.write_text(
        _render_markdown(payload, baseline),
        encoding="utf-8",
    )
    print(
        f"wrote {len(results)} samples: JSON "
        f"{payload['summary']['json_valid']}/{len(results)}, contract "
        f"{payload['summary']['contract_valid']}/{len(results)}, "
        f"{wall_seconds:.2f}s",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3.6:27b")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--baseline-json", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--ollama-url", default=OLLAMA_URL)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
