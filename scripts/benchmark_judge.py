"""Measure gpt-oss judge repeatability on teacher benchmark samples."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "reports" / "m2_teacher_benchmark.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "m2_judge_benchmark.json"
OLLAMA_URL = "http://127.0.0.1:11434"


class JudgeOutput(BaseModel):
    """Structured independent quality verdict."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    intent_correct: bool
    slots_correct: bool
    natural: bool
    reason: str


def _select_samples(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    runs = payload["runs"]
    best = max(runs, key=lambda run: run["aggregate_tokens_per_second"])
    return best["results"]


def _prompt(sample: dict[str, Any]) -> str:
    compact = {
        "source": sample["expected"],
        "candidate": sample["output"],
    }
    return (
        "Audit this synthetic Taiwan Mandarin NLU paraphrase. Accept only if the "
        "candidate keeps the source intent exactly, keeps the identical slot "
        "(type, value) pairs, every slot value appears in candidate utt, and the "
        "utterance is natural Traditional Chinese. Return a concise structured verdict.\n"
        + json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    )


async def _judge_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    *,
    model: str,
    sample: dict[str, Any],
    request_seed: int,
    num_ctx: int,
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
                            "You are an independent NLU data quality judge. "
                            "Reason conservatively and return JSON only."
                        ),
                    },
                    {"role": "user", "content": _prompt(sample)},
                ],
                "stream": False,
                "format": JudgeOutput.model_json_schema(),
                "options": {
                    "temperature": 0,
                    "seed": request_seed,
                    "num_ctx": num_ctx,
                    "num_predict": 512,
                },
            },
        )
        elapsed = time.perf_counter() - started
        response.raise_for_status()
        envelope = response.json()
        content = envelope["message"]["content"]
        parsed: JudgeOutput | None = None
        error: str | None = None
        try:
            parsed = JudgeOutput.model_validate_json(content)
        except ValidationError as exc:
            error = str(exc)
        return {
            "seed_id": sample["seed_id"],
            "verdict": parsed.model_dump() if parsed else content,
            "json_valid": parsed is not None,
            "validation_error": error,
            "done_reason": envelope.get("done_reason"),
            "thinking_chars": len(envelope["message"].get("thinking", "")),
            "wall_seconds": elapsed,
            "eval_count": envelope.get("eval_count", 0),
            "eval_duration_ns": envelope.get("eval_duration", 0),
        }


def _decision(verdict: dict[str, Any]) -> tuple[bool, ...] | None:
    value = verdict["verdict"]
    if not isinstance(value, dict):
        return None
    return (
        value["accepted"],
        value["intent_correct"],
        value["slots_correct"],
        value["natural"],
    )


async def async_main(args: argparse.Namespace) -> int:
    samples = _select_samples(args.input)
    timeout = httpx.Timeout(args.timeout)
    passes: list[dict[str, Any]] = []
    async with httpx.AsyncClient(base_url=args.ollama_url, timeout=timeout) as client:
        for pass_index, base_seed in enumerate(args.pass_seed, start=1):
            semaphore = asyncio.Semaphore(args.concurrency)
            started = time.perf_counter()
            results = await asyncio.gather(
                *(
                    _judge_one(
                        client,
                        semaphore,
                        model=args.model,
                        sample=sample,
                        request_seed=base_seed + index,
                        num_ctx=args.num_ctx,
                    )
                    for index, sample in enumerate(samples)
                )
            )
            elapsed = time.perf_counter() - started
            eval_tokens = sum(result["eval_count"] for result in results)
            passes.append(
                {
                    "pass": pass_index,
                    "base_seed": base_seed,
                    "wall_seconds": elapsed,
                    "aggregate_tokens_per_second": eval_tokens / elapsed,
                    "json_valid_count": sum(result["json_valid"] for result in results),
                    "results": results,
                }
            )
            print(
                f"judge pass {pass_index}: JSON {passes[-1]['json_valid_count']}/{len(results)}",
                flush=True,
            )

    decisions_a = {_result["seed_id"]: _decision(_result) for _result in passes[0]["results"]}
    decisions_b = {_result["seed_id"]: _decision(_result) for _result in passes[1]["results"]}
    comparable = [
        seed_id
        for seed_id in decisions_a
        if decisions_a[seed_id] is not None and decisions_b.get(seed_id) is not None
    ]
    consistent = sum(decisions_a[seed_id] == decisions_b[seed_id] for seed_id in comparable)
    output = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "source": str(args.input.relative_to(REPO_ROOT)),
        "samples": len(samples),
        "decision_consistency_count": consistent,
        "decision_consistency_rate": consistent / len(comparable) if comparable else 0.0,
        "passes": passes,
    }
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"decision consistency {consistent}/{len(comparable)}; wrote {args.output}",
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-oss:20b")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--pass-seed", type=int, nargs=2, default=[31_415, 27_182])
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--ollama-url", default=OLLAMA_URL)
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
