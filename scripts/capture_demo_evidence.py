"""Inspect or capture real M11 base-versus-adapter comparison evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.gpu_safety import assert_safe_gpu_launch, gpu_snapshot, safety_status
from src.inference.demo import (
    DEFAULT_ADAPTER,
    GemmaComparisonRuntime,
    MockComparisonRuntime,
)
from src.training.train import REPO_ROOT

CONFIRMATION = "M11-DEMO-EVIDENCE-4090"
DEFAULT_JSON = REPO_ROOT / "reports" / "m11_demo_evidence.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports" / "m11_demo_evidence.md"
UTTERANCES = (
    "播放周杰倫",
    "搜尋周杰倫的歌",
    "明天早上七點叫我起床",
    "台北明天會不會下雨",
    "幫我寄信給小美說會晚到",
)


def _tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(file for file in path.rglob("*") if file.is_file()):
        digest.update(str(child.relative_to(path)).replace("\\", "/").encode())
        with child.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def capture(runtime: Any, utterances: tuple[str, ...] = UTTERANCES) -> list[dict[str, Any]]:
    rows = []
    for utterance in utterances:
        rows.append(
            {
                "utterance": utterance,
                "base": asdict(runtime.predict(utterance, adapted=False)),
                "adapted": asdict(runtime.predict(utterance, adapted=True)),
            }
        )
    return rows


def build_report(
    *,
    rows: list[dict[str, Any]],
    adapter_dir: Path,
    runtime_mode: str,
    gpu: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if runtime_mode == "real" else "mock_validation",
        "runtime_mode": runtime_mode,
        "model": "google/gemma-4-E4B-it",
        "adapter_dir": str(adapter_dir),
        "adapter_tree_sha256": (
            _tree_digest(adapter_dir) if adapter_dir.is_dir() else None
        ),
        "prompt_template": "formosanlu_nlu.v1",
        "unconstrained_decoding": True,
        "gpu": gpu,
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip(),
        "comparisons": rows,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# M11 real comparison evidence",
        "",
        f"Status: **{payload['status']}**",
        "",
        "| Utterance | Base intent | Adapted intent | Base latency | Adapted latency |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for row in payload["comparisons"]:
        lines.append(
            f"| {row['utterance']} | `{row['base']['intent']}` | "
            f"`{row['adapted']['intent']}` | {row['base']['latency_ms']:.0f} ms | "
            f"{row['adapted']['latency_ms']:.0f} ms |"
        )
    lines.extend(
        [
            "",
            "Both paths use unconstrained generation. The base path receives the frozen "
            "zero-shot label catalog; the adapted path uses the frozen SFT prompt.",
            "",
        ]
    )
    return "\n".join(lines)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--confirm", help=f"Required with --execute: {CONFIRMATION}")
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "utterances": list(UTTERANCES),
                "adapter": str(DEFAULT_ADAPTER),
                "gpu_safety": safety_status(),
                "execute": args.execute,
                "mock": args.mock,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.execute:
        return 0
    if args.confirm != CONFIRMATION:
        raise RuntimeError(f"M11 evidence requires exact --confirm {CONFIRMATION}")
    if args.mock:
        runtime: Any = MockComparisonRuntime()
        runtime_mode = "mock"
        gpu = None
    else:
        assert_safe_gpu_launch()
        runtime = GemmaComparisonRuntime()
        runtime_mode = "real"
        gpu = gpu_snapshot()
    payload = build_report(
        rows=capture(runtime),
        adapter_dir=DEFAULT_ADAPTER,
        runtime_mode=runtime_mode,
        gpu=gpu,
    )
    _write(args.json, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    _write(args.markdown, render_markdown(payload))
    print(f"M11 evidence status={payload['status']}; rows={len(payload['comparisons'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
