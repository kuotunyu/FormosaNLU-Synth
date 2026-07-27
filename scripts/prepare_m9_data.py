"""Validate all six M9 data groups and write a reproducible preflight report."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.training.data import group_examples
from src.training.train import DEFAULT_CONFIG, load_train_config

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = REPO_ROOT / "reports" / "m9_data_preflight.json"


def _digest_rows(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    config = load_train_config(args.config)
    groups: dict[str, Any] = {}
    for group in config["groups"]:
        rows = group_examples(group, seed=int(config["training"]["seed"]))
        intents = Counter(row["intent"] for row in rows)
        groups[group] = {
            "rows": len(rows),
            "unique_ids": len({row["id"] for row in rows}),
            "intent_count": len(intents),
            "min_rows_per_intent": min(intents.values()),
            "max_rows_per_intent": max(intents.values()),
            "sha256": _digest_rows(rows),
        }
    filtered_added = groups["real_syn_filtered"]["rows"] - groups["real_only"]["rows"]
    equal_n_added = groups["real_syn_unfiltered_eqn"]["rows"] - groups["real_only"]["rows"]
    standard_added = groups["real_std_aug"]["rows"] - groups["real_only"]["rows"]
    if len({filtered_added, equal_n_added, standard_added}) != 1:
        raise AssertionError("Filtered, equal-N, and Standard Aug additions are not equal-N")
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready",
        "seed": int(config["training"]["seed"]),
        "groups": groups,
        "fairness_checks": {
            "filtered_added": filtered_added,
            "unfiltered_equal_n_added": equal_n_added,
            "standard_aug_added": standard_added,
            "equal_n": True,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"validated {len(groups)} M9 groups; equal-N additions={filtered_added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
