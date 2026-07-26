"""Plan the six compute-matched training groups without starting M9."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.training.train import DEFAULT_CONFIG, REPO_ROOT, load_train_config


@dataclass(frozen=True)
class RunSpec:
    group: str
    seed: int
    output_dir: Path
    shared_config_sha256: str


def shared_config_digest(config: dict[str, Any]) -> str:
    shared = {key: value for key, value in config.items() if key != "groups"}
    encoded = json.dumps(
        shared,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_run_plan(config_path: Path = DEFAULT_CONFIG) -> list[RunSpec]:
    config = load_train_config(config_path)
    digest = shared_config_digest(config)
    seed = int(config["training"]["seed"])
    return [
        RunSpec(
            group=group,
            seed=seed,
            output_dir=REPO_ROOT / "runs" / group / f"seed_{seed}",
            shared_config_sha256=digest,
        )
        for group in config["groups"]
    ]
