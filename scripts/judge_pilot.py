"""Judge a deterministic 50-sample pilot audit with local gpt-oss."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "filtered" / "pilot_f1_f4.jsonl"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "m4_pilot_judge.json"
OLLAMA_URL = "http://127.0.0.1:11434"


class JudgeOutput(BaseModel):
    """Independent F7 quality verdict."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    intent_correct: bool
    slots_correct: bool
    natural: bool
    reason: str


def _load_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def select_audit_records(
    records: list[dict[str, Any]],
    *,
    count: int = 50,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Prioritize hard negatives, then stratify the remainder by recipe."""
    if len(records) < count:
        raise ValueError(f"Need {count} records, only {len(records)} available")
    rng = random.Random(seed)
    hard = [
        record for record in records if record["sample"]["provenance"]["recipe"] == "hard_negative"
    ]
    rng.shuffle(hard)
    selected = hard[: min(25, count)]
    selected_ids = {record["sample"]["id"] for record in selected}

    by_recipe: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if record["sample"]["id"] in selected_ids:
            continue
        recipe = record["sample"]["provenance"]["recipe"]
        by_recipe.setdefault(recipe, []).append(record)
    for values in by_recipe.values():
        rng.shuffle(values)

    recipe_order = sorted(by_recipe)
    cursor = 0
    while len(selected) < count:
        recipe = recipe_order[cursor % len(recipe_order)]
        if by_recipe[recipe]:
            record = by_recipe[recipe].pop()
            selected.append(record)
            selected_ids.add(record["sample"]["id"])
        cursor += 1
        if cursor > len(records) * 2:
            raise RuntimeError("Could not fill judge audit sample")
    return selected


async def _model_digest(client: httpx.AsyncClient, model: str) -> str:
    response = await client.get("/api/tags")
    response.raise_for_status()
    for entry in response.json().get("models", []):
        if entry.get("name") == model or entry.get("model") == model:
            return str(entry.get("digest", "unknown"))
    raise RuntimeError(f"Model is not installed in Ollama: {model}")


def _prompt(record: dict[str, Any]) -> str:
    payload = {
        "expected_labels": record["expected"],
        "candidate": {
            "utt": record["sample"]["utt"],
            "intent": record["sample"]["intent"],
            "slots": record["sample"]["slots"],
            "style": record["sample"]["style"],
            "recipe": record["sample"]["provenance"]["recipe"],
        },
    }
    return (
        "Audit this synthetic Taiwan Mandarin NLU example. Accept only when: "
        "(1) intent exactly matches expected, (2) slots exactly match expected and each "
        "literal value is grounded, (3) the utterance is a complete natural request for "
        "its declared style, and (4) hard negatives unambiguously express the target "
        "action. Reject word salad, translation errors, vague fragments, wrong actions, "
        "and unnatural particle placement. In this dataset, hard_negative is a recipe "
        "name for a correctly labeled target example near a confusable intent; it is not "
        "a negative label and must not be rejected merely because of that recipe name. "
        "Return a concise structured verdict.\n"
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )


async def _judge_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    *,
    record: dict[str, Any],
    model: str,
    request_seed: int,
    num_ctx: int,
    num_predict: int,
) -> dict[str, Any]:
    async with semaphore:
        started = time.perf_counter()
        response = await client.post(
            "/api/chat",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Reasoning: low\n"
                            "You are an independent Taiwan Mandarin NLU data judge. "
                            "Be conservative and return JSON only."
                        ),
                    },
                    {"role": "user", "content": _prompt(record)},
                ],
                "stream": False,
                "format": JudgeOutput.model_json_schema(),
                "options": {
                    "temperature": 0,
                    "seed": request_seed,
                    "num_ctx": num_ctx,
                    "num_predict": num_predict,
                },
            },
        )
        wall_seconds = time.perf_counter() - started
    response.raise_for_status()
    envelope = response.json()
    content = envelope["message"]["content"]
    verdict: JudgeOutput | None = None
    error: str | None = None
    try:
        verdict = JudgeOutput.model_validate_json(content)
    except ValidationError as exc:
        error = str(exc)
    return {
        "generation_index": record["generation_index"],
        "sample_id": record["sample"]["id"],
        "recipe": record["sample"]["provenance"]["recipe"],
        "utt": record["sample"]["utt"],
        "verdict": verdict.model_dump() if verdict else content,
        "json_valid": verdict is not None,
        "validation_error": error,
        "wall_seconds": wall_seconds,
        "eval_count": envelope.get("eval_count", 0),
        "eval_duration_ns": envelope.get("eval_duration", 0),
        "thinking_chars": len(envelope["message"].get("thinking", "")),
    }


async def async_main(args: argparse.Namespace) -> int:
    records = _load_records(args.input)
    selected = select_audit_records(records, count=args.count, seed=args.selection_seed)
    timeout = httpx.Timeout(args.timeout)
    started = time.perf_counter()
    async with httpx.AsyncClient(base_url=args.ollama_url, timeout=timeout) as client:
        digest = await _model_digest(client, args.model)
        semaphore = asyncio.Semaphore(args.concurrency)
        results = await asyncio.gather(
            *(
                _judge_one(
                    client,
                    semaphore,
                    record=record,
                    model=args.model,
                    request_seed=61_000 + index,
                    num_ctx=args.num_ctx,
                    num_predict=args.num_predict,
                )
                for index, record in enumerate(selected)
            )
        )
    elapsed = time.perf_counter() - started
    accepted = sum(
        isinstance(result["verdict"], dict) and result["verdict"]["accepted"] for result in results
    )
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "model_digest": digest,
        "source": str(args.input.relative_to(REPO_ROOT)),
        "selection_seed": args.selection_seed,
        "selection_recipe_counts": dict(
            sorted(Counter(result["recipe"] for result in results).items())
        ),
        "summary": {
            "samples": len(results),
            "json_valid": sum(result["json_valid"] for result in results),
            "accepted": accepted,
            "accepted_rate": accepted / len(results),
            "wall_seconds": elapsed,
            "output_tokens": sum(result["eval_count"] for result in results),
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"judge accepted {accepted}/{len(results)} "
        f"({accepted / len(results):.1%}), JSON "
        f"{payload['summary']['json_valid']}/{len(results)}, {elapsed:.2f}s",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default="gpt-oss:20b")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--selection-seed", type=int, default=42)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--num-predict", type=int, default=768)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--ollama-url", default=OLLAMA_URL)
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
