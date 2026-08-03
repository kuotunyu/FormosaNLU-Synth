"""Publish only the two v1.2.1 Hugging Face cards behind immutable guards."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from huggingface_hub import HfApi

from scripts.hf_release import DATASET_REPO_ID, MODEL_REPO_ID, REPO_ROOT
from scripts.verify_publication import (
    EXPECTED_ADAPTER_SHA256,
    EXPECTED_DATASET_SHA256,
    verify_publication,
)

CONFIRMATION_TOKEN = "HF-CARDS-V1.2.1"
EXPECTED_ADAPTER_BYTES = 155_609_536
DATASET_CARD = REPO_ROOT / "hf_cards" / "dataset_README.md"
MODEL_CARD = REPO_ROOT / "hf_cards" / "model_README.md"
DEFAULT_REPORT = REPO_ROOT / "outputs" / "publication" / "v1.2.1" / "hf_card_update.json"


@dataclass(frozen=True)
class RemoteSnapshot:
    """Remote state that a card-only update is forbidden to change."""

    files: frozenset[str]
    revision: str
    dataset_sha256: str | None = None
    adapter_sha256: str | None = None
    adapter_bytes: int | None = None


def validate_confirmation(value: str) -> None:
    """Reject ambiguous execution confirmation."""
    if value != CONFIRMATION_TOKEN:
        raise ValueError(f"Exact confirmation required: {CONFIRMATION_TOKEN}")


def assert_safe_delta(before: RemoteSnapshot, after: RemoteSnapshot) -> None:
    """Allow only the card commit revision to change."""
    immutable_fields = (
        "files",
        "dataset_sha256",
        "adapter_sha256",
        "adapter_bytes",
    )
    changed = [
        field
        for field in immutable_fields
        if getattr(before, field) != getattr(after, field)
    ]
    if changed:
        raise ValueError(f"Hugging Face immutable state changed: {', '.join(changed)}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshots(evidence: dict[str, Any]) -> dict[str, RemoteSnapshot]:
    dataset = evidence["dataset"]
    model = evidence["model"]
    return {
        "dataset": RemoteSnapshot(
            files=frozenset(dataset["files"]),
            revision=str(dataset["hub_commit"]),
            dataset_sha256=str(dataset["train_sha256"]),
        ),
        "model": RemoteSnapshot(
            files=frozenset(model["files"]),
            revision=str(model["hub_commit"]),
            adapter_sha256=str(model["adapter_sha256"]),
            adapter_bytes=int(model["adapter_bytes"]),
        ),
    }


def _serializable(snapshot: RemoteSnapshot) -> dict[str, Any]:
    payload = asdict(snapshot)
    payload["files"] = sorted(snapshot.files)
    return payload


def _load_token() -> str:
    token = os.environ.get("HF_TOKEN")
    if not token:
        token = str(dotenv_values(REPO_ROOT.parent / ".env").get("HF_TOKEN") or "")
    if not token:
        raise ValueError("HF_TOKEN is missing from the environment and parent .env")
    return token


def _plan(before: dict[str, RemoteSnapshot]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mode": "card_only",
        "confirmation": CONFIRMATION_TOKEN,
        "writes": [
            {
                "repo_id": DATASET_REPO_ID,
                "repo_type": "dataset",
                "source": DATASET_CARD.relative_to(REPO_ROOT).as_posix(),
                "source_sha256": _sha256(DATASET_CARD),
                "remote_path": "README.md",
            },
            {
                "repo_id": MODEL_REPO_ID,
                "repo_type": "model",
                "source": MODEL_CARD.relative_to(REPO_ROOT).as_posix(),
                "source_sha256": _sha256(MODEL_CARD),
                "remote_path": "README.md",
            },
        ],
        "immutable_expectations": {
            "dataset_train_sha256": EXPECTED_DATASET_SHA256,
            "adapter_sha256": EXPECTED_ADAPTER_SHA256,
            "adapter_bytes": EXPECTED_ADAPTER_BYTES,
            "dataset_file_set": sorted(before["dataset"].files),
            "model_file_set": sorted(before["model"].files),
        },
        "before": {key: _serializable(value) for key, value in before.items()},
    }


def publish_cards() -> dict[str, Any]:
    """Upload two README files and prove immutable artifacts did not change."""
    before_evidence = verify_publication()
    before = _snapshots(before_evidence)
    plan = _plan(before)
    token = _load_token()
    api = HfApi(token=token)
    commits: dict[str, str] = {}
    for repo_id, repo_type, source in (
        (DATASET_REPO_ID, "dataset", DATASET_CARD),
        (MODEL_REPO_ID, "model", MODEL_CARD),
    ):
        result = api.upload_file(
            path_or_fileobj=source,
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="Docs: update v1.2.1 evidence card",
        )
        commits[repo_id] = str(result)

    after_evidence = verify_publication()
    after = _snapshots(after_evidence)
    for key in ("dataset", "model"):
        assert_safe_delta(before[key], after[key])

    report = {
        **plan,
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "remote_commits": commits,
        "after": {key: _serializable(value) for key, value in after.items()},
    }
    DEFAULT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Upload both card files.")
    parser.add_argument("--confirm", default="", help="Exact destructive-action token.")
    args = parser.parse_args()

    before = _snapshots(verify_publication())
    plan = _plan(before)
    if not args.execute:
        plan["status"] = "dry_run"
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    validate_confirmation(args.confirm)
    report = publish_cards()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
