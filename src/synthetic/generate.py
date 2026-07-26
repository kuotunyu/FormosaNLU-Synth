"""Async, resumable Ollama generation for FormosaNLU."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from src.data.load_massive import DEFAULT_DATA_DIR
from src.data.normalize import contains_normalized
from src.synthetic.checkpoint import CheckpointError, JsonlCheckpoint
from src.synthetic.planning import DEFAULT_MANIFEST, build_generation_plans
from src.synthetic.recipes import RecipePlan
from src.synthetic.schema import (
    CandidateOutput,
    GenerationParams,
    Provenance,
    SyntheticSample,
    content_address,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PILOT_OUTPUT = REPO_ROOT / "data" / "generated" / "pilot.jsonl"
DEFAULT_FULL_OUTPUT = REPO_ROOT / "data" / "generated" / "full_unfiltered.jsonl"
DEFAULT_COST_LOG = REPO_ROOT / "logs" / "cost.json"
OLLAMA_URL = "http://127.0.0.1:11434"
FULL_GENERATION_COUNT = 18_000


def plan_fingerprint(plan: RecipePlan, request_seed: int) -> str:
    payload = {
        "recipe": plan.recipe,
        "prompt_version": plan.prompt_version,
        "style": plan.style,
        "system_prompt": plan.system_prompt,
        "user_prompt": plan.user_prompt,
        "expected_intent": plan.expected_intent,
        "expected_slots": plan.expected_slots,
        "seed_sample_id": plan.seed_sample_id,
        "pair_id": plan.pair_id,
        "request_seed": request_seed,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def _model_digest(client: httpx.AsyncClient, model: str) -> str:
    response = await client.get("/api/tags")
    response.raise_for_status()
    for entry in response.json().get("models", []):
        if entry.get("name") == model or entry.get("model") == model:
            return str(entry.get("digest", "unknown"))
    raise RuntimeError(f"Model is not installed in Ollama: {model}")


def _contract_reason(candidate: CandidateOutput, plan: RecipePlan) -> str | None:
    if candidate.intent != plan.expected_intent:
        return "F2_INTENT_CONTRACT"
    if sorted((slot.type, slot.value) for slot in candidate.slots) != sorted(
        plan.expected_slots
    ):
        return "F2_SLOT_CONTRACT"
    if not all(contains_normalized(candidate.utt, slot.value) for slot in candidate.slots):
        return "F3_UNGROUNDED_SLOT"
    return None


async def _generate_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    *,
    index: int,
    plan: RecipePlan,
    model: str,
    model_digest: str,
    num_ctx: int,
    temperature: float,
    top_p: float,
) -> dict[str, Any]:
    request_seed = 50_000 + index
    started_at = datetime.now(timezone.utc)
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

    contract_reason = _contract_reason(candidate, plan) if candidate else "F1_SCHEMA_INVALID"
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
            filter_score={},
            filter_stage_passed=None,
            reject_reason=None,
            generated_at=started_at,
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
        "schema_version": 1,
        "generation_index": index,
        "plan_fingerprint": plan_fingerprint(plan, request_seed),
        "expected": {
            "intent": plan.expected_intent,
            "slots": [
                {"type": slot_type, "value": value}
                for slot_type, value in plan.expected_slots
            ],
        },
        "sample": sample.model_dump(mode="json") if sample else None,
        "raw_content": None if sample else content,
        "generation_contract_reason": contract_reason,
        "validation_error": validation_error,
        "metrics": {
            "wall_seconds": wall_seconds,
            "prompt_eval_count": envelope.get("prompt_eval_count", 0),
            "eval_count": envelope.get("eval_count", 0),
            "prompt_eval_duration_ns": envelope.get("prompt_eval_duration", 0),
            "eval_duration_ns": envelope.get("eval_duration", 0),
        },
    }


def _validate_resume_records(
    records: dict[int, dict[str, Any]],
    plans: list[RecipePlan],
) -> None:
    for index, record in records.items():
        if index < 0 or index >= len(plans):
            raise CheckpointError(
                f"Checkpoint index {index} is outside current plan size {len(plans)}"
            )
        expected = plan_fingerprint(plans[index], 50_000 + index)
        if record.get("plan_fingerprint") != expected:
            raise CheckpointError(
                f"Plan drift at generation_index {index}; use another output path"
            )


def _update_cost_log(
    path: Path,
    *,
    output: Path,
    model: str,
    target_records: int,
    started_at: str,
    wall_seconds: float,
    new_records: int,
    complete_records: int,
    prompt_tokens: int,
    output_tokens: int,
    status: str,
    error: str | None,
) -> None:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {"schema_version": 1, "api_cost_usd": 0.0, "sessions": []}
    payload["sessions"].append(
        {
            "started_at": started_at,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "output": str(output.relative_to(REPO_ROOT)),
            "target_records": target_records,
            "new_records": new_records,
            "complete_records": complete_records,
            "wall_seconds": wall_seconds,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "api_cost_usd": 0.0,
            "status": status,
            "error": error,
        }
    )
    payload["total_gpu_wall_seconds"] = sum(
        session["wall_seconds"] for session in payload["sessions"]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


async def async_main(args: argparse.Namespace) -> int:
    total = args.pilot if args.pilot is not None else FULL_GENERATION_COUNT
    output = args.output or (
        DEFAULT_PILOT_OUTPUT if args.pilot is not None else DEFAULT_FULL_OUTPUT
    )
    if not output.is_absolute():
        output = REPO_ROOT / output
    cost_log = args.cost_log
    if not cost_log.is_absolute():
        cost_log = REPO_ROOT / cost_log
    plans = build_generation_plans(
        total,
        manifest_path=args.manifest,
        data_dir=args.data_dir,
        schedule_seed=args.schedule_seed,
    )
    checkpoint = JsonlCheckpoint(output)
    existing = checkpoint.load()
    _validate_resume_records(existing, plans)
    missing = [index for index in range(total) if index not in existing]
    if args.max_new is not None:
        missing = missing[: args.max_new]
    if not missing:
        print(f"already complete: {len(existing)}/{total} records")
        return 0

    timeout = httpx.Timeout(args.timeout)
    started_iso = datetime.now(timezone.utc).isoformat()
    started = time.perf_counter()
    completed_new: list[dict[str, Any]] = []
    write_lock = asyncio.Lock()
    status = "complete"
    error: str | None = None
    try:
        async with httpx.AsyncClient(base_url=args.ollama_url, timeout=timeout) as client:
            digest = await _model_digest(client, args.model)
            semaphore = asyncio.Semaphore(args.concurrency)

            async def run_and_checkpoint(index: int) -> None:
                record = await _generate_one(
                    client,
                    semaphore,
                    index=index,
                    plan=plans[index],
                    model=args.model,
                    model_digest=digest,
                    num_ctx=args.num_ctx,
                    temperature=args.temperature,
                    top_p=args.top_p,
                )
                async with write_lock:
                    checkpoint.append(record)
                    completed_new.append(record)
                    if len(completed_new) % 25 == 0:
                        print(
                            f"checkpointed {len(existing) + len(completed_new)}/{total}",
                            flush=True,
                        )

            await asyncio.gather(*(run_and_checkpoint(index) for index in missing))
        checkpoint.compact()
    except BaseException as exc:
        status = (
            "interrupted"
            if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt))
            else "error"
        )
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        elapsed = time.perf_counter() - started
        complete_records = len(checkpoint.load())
        _update_cost_log(
            cost_log,
            output=output,
            model=args.model,
            target_records=total,
            started_at=started_iso,
            wall_seconds=elapsed,
            new_records=len(completed_new),
            complete_records=complete_records,
            prompt_tokens=sum(
                record["metrics"]["prompt_eval_count"] for record in completed_new
            ),
            output_tokens=sum(
                record["metrics"]["eval_count"] for record in completed_new
            ),
            status=status,
            error=error,
        )
    print(
        f"generated {len(completed_new)} new records in {elapsed:.2f}s; "
        f"checkpoint now {complete_records}/{total}",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", type=int, metavar="N")
    mode.add_argument("--full", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-new", type=int)
    parser.add_argument("--model", default="qwen3.6:27b")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--cost-log", type=Path, default=DEFAULT_COST_LOG)
    parser.add_argument("--ollama-url", default=OLLAMA_URL)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--schedule-seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    if args.pilot is not None and args.pilot <= 0:
        parser.error("--pilot must be positive")
    if args.max_new is not None and args.max_new <= 0:
        parser.error("--max-new must be positive")
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
