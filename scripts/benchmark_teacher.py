"""Benchmark an Ollama teacher on 20 frozen real train seeds."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from src.data.load_massive import DEFAULT_DATA_DIR, decode_example, load_massive_split
from src.data.normalize import contains_normalized, parse_annotated_utterance

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "splits" / "manifest.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "m2_teacher_benchmark.json"
OLLAMA_URL = "http://127.0.0.1:11434"


class GeneratedSlot(BaseModel):
    """One generated slot label."""

    model_config = ConfigDict(extra="forbid")

    type: str
    value: str


class TeacherOutput(BaseModel):
    """Small benchmark schema, later extended with provenance at M3."""

    model_config = ConfigDict(extra="forbid")

    utt: str
    intent: str
    slots: list[GeneratedSlot]


def _load_seeds(manifest_path: Path, data_dir: Path) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected_by_intent = manifest["splits"]["train_20shot_by_intent"]
    seed_ids = [selected_by_intent[intent][0] for intent in sorted(selected_by_intent)[:20]]
    dataset = load_massive_split("train", data_dir, download=False)
    index_by_id = {sample_id: index for index, sample_id in enumerate(dataset["id"])}
    seeds: list[dict[str, Any]] = []
    for sample_id in seed_ids:
        example = decode_example(dataset, index_by_id[sample_id])
        parsed = parse_annotated_utterance(example["annot_utt"])
        seeds.append(
            {
                "id": example["id"],
                "utt": example["utt"],
                "intent": example["intent"],
                "slots": [{"type": slot_type, "value": value} for slot_type, value in parsed.slots],
            }
        )
    return seeds


def _prompt(seed: dict[str, Any]) -> str:
    payload = json.dumps(seed, ensure_ascii=False, separators=(",", ":"))
    return (
        "Rewrite this Traditional Chinese (Taiwan) NLU seed into one natural paraphrase. "
        "Keep the intent exactly unchanged. Keep every slot type and literal slot value "
        "exactly unchanged and ensure each value appears in utt. Do not add slots. "
        "Return only the requested JSON object.\n"
        f"Seed: {payload}"
    )


async def _generate(
    client: httpx.AsyncClient,
    *,
    model: str,
    seed: dict[str, Any],
    request_seed: int,
    num_ctx: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    response = await client.post(
        "/api/chat",
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate label-preserving Taiwan Mandarin NLU examples. "
                        "Return valid JSON only."
                    ),
                },
                {"role": "user", "content": _prompt(seed)},
            ],
            "stream": False,
            "think": False,
            "format": TeacherOutput.model_json_schema(),
            "options": {
                "temperature": 0,
                "seed": request_seed,
                "num_ctx": num_ctx,
                "num_predict": 180,
            },
        },
    )
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    envelope = response.json()
    content = envelope["message"]["content"]
    parsed: TeacherOutput | None = None
    validation_error: str | None = None
    try:
        parsed = TeacherOutput.model_validate_json(content)
    except ValidationError as exc:
        validation_error = str(exc)

    task_valid = False
    if parsed is not None:
        expected_slots = sorted((slot["type"], slot["value"]) for slot in seed["slots"])
        actual_slots = sorted((slot.type, slot.value) for slot in parsed.slots)
        grounded = all(contains_normalized(parsed.utt, slot.value) for slot in parsed.slots)
        task_valid = parsed.intent == seed["intent"] and actual_slots == expected_slots and grounded

    return {
        "seed_id": seed["id"],
        "expected": seed,
        "output": parsed.model_dump() if parsed else content,
        "json_valid": parsed is not None,
        "task_valid": task_valid,
        "validation_error": validation_error,
        "wall_seconds": elapsed,
        "prompt_eval_count": envelope.get("prompt_eval_count", 0),
        "eval_count": envelope.get("eval_count", 0),
        "prompt_eval_duration_ns": envelope.get("prompt_eval_duration", 0),
        "eval_duration_ns": envelope.get("eval_duration", 0),
        "load_duration_ns": envelope.get("load_duration", 0),
    }


def _gpu_memory_mib() -> float | None:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=3,
        )
        return float(completed.stdout.strip().splitlines()[0])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


async def _monitor_memory(
    client: httpx.AsyncClient,
    stop: asyncio.Event,
    model: str,
) -> dict[str, float]:
    peak_gpu_mib = 0.0
    peak_model_vram_mib = 0.0
    while not stop.is_set():
        total_used = await asyncio.to_thread(_gpu_memory_mib)
        if total_used is not None:
            peak_gpu_mib = max(peak_gpu_mib, total_used)
        try:
            response = await client.get("/api/ps")
            response.raise_for_status()
            for resident in response.json().get("models", []):
                if resident.get("name") == model:
                    model_mib = float(resident.get("size_vram", 0)) / (1024**2)
                    peak_model_vram_mib = max(peak_model_vram_mib, model_mib)
        except httpx.HTTPError:
            pass
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=0.5)
    return {
        "peak_gpu_memory_mib": peak_gpu_mib,
        "peak_ollama_model_vram_mib": peak_model_vram_mib,
    }


async def _run_concurrency(
    client: httpx.AsyncClient,
    *,
    model: str,
    seeds: list[dict[str, Any]],
    concurrency: int,
    num_ctx: int,
) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency)

    async def guarded(index: int, seed: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await _generate(
                client,
                model=model,
                seed=seed,
                request_seed=42_000 + index,
                num_ctx=num_ctx,
            )

    # Exclude model loading and graph initialization from the measured batch.
    await _generate(
        client,
        model=model,
        seed=seeds[0],
        request_seed=41_999,
        num_ctx=num_ctx,
    )
    stop = asyncio.Event()
    monitor = asyncio.create_task(_monitor_memory(client, stop, model))
    started = time.perf_counter()
    results = await asyncio.gather(*(guarded(index, seed) for index, seed in enumerate(seeds)))
    wall_seconds = time.perf_counter() - started
    stop.set()
    memory = await monitor

    eval_tokens = sum(result["eval_count"] for result in results)
    eval_duration_ns = sum(result["eval_duration_ns"] for result in results)
    return {
        "model": model,
        "client_concurrency": concurrency,
        "num_ctx": num_ctx,
        "samples": len(results),
        "wall_seconds": wall_seconds,
        "eval_tokens": eval_tokens,
        "aggregate_tokens_per_second": eval_tokens / wall_seconds,
        "summed_eval_tokens_per_second": (
            eval_tokens / (eval_duration_ns / 1e9) if eval_duration_ns else 0.0
        ),
        "json_valid_count": sum(result["json_valid"] for result in results),
        "task_valid_count": sum(result["task_valid"] for result in results),
        **memory,
        "results": results,
    }


async def async_main(args: argparse.Namespace) -> int:
    seeds = _load_seeds(args.manifest, args.data_dir)
    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(base_url=args.ollama_url, timeout=timeout) as client:
        runs = []
        for concurrency in args.concurrency:
            print(f"benchmarking {args.model} at concurrency={concurrency}", flush=True)
            run = await _run_concurrency(
                client,
                model=args.model,
                seeds=seeds,
                concurrency=concurrency,
                num_ctx=args.num_ctx,
            )
            runs.append(run)
            print(
                f"  {run['aggregate_tokens_per_second']:.2f} tok/s, "
                f"JSON {run['json_valid_count']}/{run['samples']}, "
                f"task {run['task_valid_count']}/{run['samples']}",
                flush=True,
            )

    output = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed_source": str(args.manifest.relative_to(REPO_ROOT)),
        "runs": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3.6:27b")
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 4, 8])
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--ollama-url", default=OLLAMA_URL)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
