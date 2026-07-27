"""Inspect or execute the resumable full-corpus F7 gpt-oss audit."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from scripts.judge_pilot import _judge_one, _model_digest
from src.synthetic.checkpoint import JsonlCheckpoint

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "data" / "filtered" / "full_f7_audit_manifest.jsonl"
DEFAULT_RESULTS = REPO_ROOT / "data" / "filtered" / "full_f7_judge_results.jsonl"
DEFAULT_REPORT = REPO_ROOT / "reports" / "m6_f7_judge.json"
OLLAMA_URL = "http://127.0.0.1:11434"
CONFIRMATION = "F7-GPT-OSS-20B"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_report(
    *,
    manifest: list[dict[str, Any]],
    completed: dict[int, dict[str, Any]],
    model: str,
    model_digest: str | None,
    output: Path,
) -> dict[str, Any]:
    ordered = [completed[row["generation_index"]] for row in manifest]
    strata: dict[str, dict[str, int | float]] = {}
    for stratum in sorted({row["selection_stratum"] for row in ordered}):
        rows = [row for row in ordered if row["selection_stratum"] == stratum]
        accepted = sum(
            isinstance(row["verdict"], dict) and row["verdict"]["accepted"] for row in rows
        )
        strata[stratum] = {
            "samples": len(rows),
            "accepted": accepted,
            "rejected": len(rows) - accepted,
            "accepted_rate": accepted / len(rows),
        }
    accepted = sum(
        isinstance(row["verdict"], dict) and row["verdict"]["accepted"] for row in ordered
    )
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "model": model,
        "model_digest": model_digest,
        "samples": len(ordered),
        "json_valid": sum(row["json_valid"] for row in ordered),
        "accepted": accepted,
        "rejected": len(ordered) - accepted,
        "accepted_rate": accepted / len(ordered),
        "selection_strata": strata,
        "recipe_counts": dict(sorted(Counter(row["recipe"] for row in ordered).items())),
        "wall_seconds_sum": sum(float(row["wall_seconds"]) for row in ordered),
        "output_tokens": sum(int(row["eval_count"]) for row in ordered),
        "random_stratum_is_rate_estimator": True,
        "targeted_strata_are_not_unbiased_rate_estimators": True,
        "rejected_sample_ids": [
            row["sample_id"]
            for row in ordered
            if isinstance(row["verdict"], dict) and not row["verdict"]["accepted"]
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


async def execute(args: argparse.Namespace, manifest: list[dict[str, Any]]) -> dict[str, Any]:
    checkpoint = JsonlCheckpoint(args.results)
    existing = checkpoint.load()
    missing = [row for row in manifest if row["generation_index"] not in existing]
    request_seeds = {
        row["generation_index"]: 71_000 + index for index, row in enumerate(manifest)
    }
    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(base_url=args.ollama_url, timeout=timeout) as client:
        digest = await _model_digest(client, args.model)
        semaphore = asyncio.Semaphore(args.concurrency)
        for start in range(0, len(missing), args.checkpoint_batch):
            batch = missing[start : start + args.checkpoint_batch]
            started = time.perf_counter()
            results = await asyncio.gather(
                *(
                    _judge_one(
                        client,
                        semaphore,
                        record=row,
                        model=args.model,
                        request_seed=request_seeds[row["generation_index"]],
                        num_ctx=args.num_ctx,
                        num_predict=args.num_predict,
                    )
                    for row in batch
                )
            )
            for source, result in zip(batch, results, strict=True):
                result["selection_stratum"] = source["f7_selection"]["stratum"]
                checkpoint.append(result)
            print(
                f"checkpointed {len(existing) + start + len(batch)}/{len(manifest)} "
                f"in {time.perf_counter() - started:.1f}s",
                flush=True,
            )
    checkpoint.compact()
    return _write_report(
        manifest=manifest,
        completed=checkpoint.load(),
        model=args.model,
        model_digest=digest,
        output=args.report,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--model", default="gpt-oss:20b")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--checkpoint-batch", type=int, default=16)
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--num-predict", type=int, default=768)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--ollama-url", default=OLLAMA_URL)
    args = parser.parse_args()
    manifest = _load_jsonl(args.manifest)
    checkpoint = JsonlCheckpoint(args.results)
    existing = checkpoint.load()
    print(f"F7 plan: {len(manifest)} rows; checkpoint {len(existing)}/{len(manifest)}")
    if args.report_only:
        missing = [row for row in manifest if row["generation_index"] not in existing]
        if missing:
            raise RuntimeError(f"F7 checkpoint incomplete: {len(missing)} rows missing")
        _write_report(
            manifest=manifest,
            completed=existing,
            model=args.model,
            model_digest=None,
            output=args.report,
        )
        return 0
    if not args.execute:
        return 0
    if args.confirm != CONFIRMATION:
        raise RuntimeError(f"F7 execution requires --confirm {CONFIRMATION}")
    result = asyncio.run(execute(args, manifest))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
