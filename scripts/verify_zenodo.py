"""Verify the public Zenodo archive created from the v1.2.1 GitHub release."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = REPO_ROOT / "reports" / "v121_zenodo.json"
ZENODO_RECORDS_API = "https://zenodo.org/api/records"
GITHUB_API = "https://api.github.com/repos/kuotunyu/FormosaNLU-Synth"
GITHUB_REPOSITORY = "https://github.com/kuotunyu/FormosaNLU-Synth"
EXPECTED_CREATOR = "kuotunyu"
EXPECTED_VERSION = "1.2.1"
EXPECTED_ZENODO_VERSION = f"v{EXPECTED_VERSION}"
DOI_PATTERN = re.compile(r"^10\.5281/zenodo\.\d+$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _get_json(url: str, *, params: dict[str, object] | None = None) -> Any:
    headers = {"Accept": "application/json", "User-Agent": "FormosaNLU-Synth"}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token and url.startswith(f"{GITHUB_API}/"):
        headers["Authorization"] = f"Bearer {github_token}"
    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _resolve_annotated_tag(version: str) -> str:
    tag_name = f"v{version}"
    reference = _get_json(f"{GITHUB_API}/git/ref/tags/{tag_name}")
    target = reference.get("object", {})
    if target.get("type") != "tag":
        raise ValueError(f"GitHub tag {tag_name} is not annotated")
    tag_object = _get_json(f"{GITHUB_API}/git/tags/{target['sha']}")
    commit = str(tag_object.get("object", {}).get("sha", ""))
    if tag_object.get("object", {}).get("type") != "commit" or not COMMIT_PATTERN.fullmatch(
        commit
    ):
        raise ValueError(f"GitHub tag {tag_name} does not resolve to a commit")
    return commit


def _software_type(metadata: dict[str, Any]) -> str:
    resource_type = metadata.get("resource_type", {})
    if isinstance(resource_type, dict):
        for key in ("id", "type"):
            value = resource_type.get(key)
            if value:
                return str(value).lower()
    return str(metadata.get("upload_type", "")).lower()


def validate_record(
    payload: dict[str, Any],
    expected_tag_commit: str,
) -> dict[str, Any]:
    """Validate one Zenodo record and return normalized public evidence."""
    if not COMMIT_PATTERN.fullmatch(expected_tag_commit):
        raise ValueError("GitHub tag commit must be a full lowercase SHA-1")

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Zenodo record metadata is missing")
    if metadata.get("version") != EXPECTED_ZENODO_VERSION:
        raise ValueError(
            "Zenodo version mismatch: "
            f"{metadata.get('version')!r} != {EXPECTED_ZENODO_VERSION!r}"
        )
    if _software_type(metadata) != "software":
        raise ValueError("Zenodo resource type is not software")

    creators = metadata.get("creators", [])
    creator_names = [str(item.get("name", "")) for item in creators if isinstance(item, dict)]
    if creator_names != [EXPECTED_CREATOR]:
        raise ValueError(f"Unexpected Zenodo creator metadata: {creator_names}")

    doi = str(payload.get("doi", ""))
    if not DOI_PATTERN.fullmatch(doi):
        raise ValueError(f"Unexpected Zenodo DOI: {doi!r}")
    concept_doi = str(payload.get("conceptdoi", ""))
    if concept_doi and not DOI_PATTERN.fullmatch(concept_doi):
        raise ValueError(f"Unexpected Zenodo concept DOI: {concept_doi!r}")

    related = metadata.get("related_identifiers", [])
    identifiers = [
        str(item.get("identifier", ""))
        for item in related
        if isinstance(item, dict)
    ]
    repository_prefix = GITHUB_REPOSITORY.lower()
    if not any(identifier.lower().startswith(repository_prefix) for identifier in identifiers):
        raise ValueError("Zenodo record is not related to the expected GitHub repository")

    raw_files = payload.get("files", [])
    files: list[dict[str, object]] = []
    for item in raw_files:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", ""))
        checksum = str(item.get("checksum", ""))
        size = int(item.get("size", 0) or 0)
        if not key or not checksum or size <= 0:
            raise ValueError("Zenodo archive file metadata is incomplete")
        files.append({"checksum": checksum, "key": key, "size": size})
    if not files:
        raise ValueError("Zenodo record has no archive files")

    record_id = payload.get("id")
    if not isinstance(record_id, int):
        raise ValueError("Zenodo record ID is missing")
    links = payload.get("links", {})
    record_url = str(links.get("html", "")) if isinstance(links, dict) else ""
    if not record_url:
        record_url = f"https://zenodo.org/records/{record_id}"

    return {
        "schema_version": 1,
        "status": "public_verified",
        "record_id": record_id,
        "record_url": record_url,
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}",
        "concept_doi": concept_doi or None,
        "concept_doi_url": f"https://doi.org/{concept_doi}" if concept_doi else None,
        "title": str(metadata.get("title", "")),
        "version": str(metadata["version"]),
        "publication_date": str(metadata.get("publication_date", "")),
        "creator_names": creator_names,
        "resource_type": "software",
        "related_identifiers": sorted(identifiers),
        "files": sorted(files, key=lambda item: str(item["key"])),
        "github_repository": GITHUB_REPOSITORY,
        "github_tag": f"v{EXPECTED_VERSION}",
        "github_tag_commit": expected_tag_commit,
    }


def verify_zenodo(
    version: str = EXPECTED_VERSION,
    record_id: int | None = None,
) -> dict[str, Any]:
    """Find and verify exactly one public Zenodo record for ``version``."""
    if version != EXPECTED_VERSION:
        raise ValueError(f"This verifier is frozen to Zenodo version {EXPECTED_VERSION}")
    tag_commit = _resolve_annotated_tag(version)
    if record_id is not None:
        if record_id <= 0:
            raise ValueError("Zenodo record ID must be a positive integer")
        record = _get_json(f"{ZENODO_RECORDS_API}/{record_id}")
        if not isinstance(record, dict):
            raise ValueError("Zenodo record response is not an object")
        report = validate_record(record, expected_tag_commit=tag_commit)
        report["verified_at"] = datetime.now(timezone.utc).isoformat()
        report["anonymous_verification"] = not bool(os.environ.get("GITHUB_TOKEN"))
        report["zenodo_api_authentication"] = "anonymous"
        report["github_api_authentication"] = (
            "token" if os.environ.get("GITHUB_TOKEN") else "anonymous"
        )
        return report

    search = _get_json(
        ZENODO_RECORDS_API,
        params={
            "q": '"FormosaNLU-Synth"',
            "all_versions": "true",
            "size": 25,
            "sort": "mostrecent",
        },
    )
    hits = search.get("hits", {}).get("hits", []) if isinstance(search, dict) else []
    matches = [
        item
        for item in hits
        if isinstance(item, dict)
        and isinstance(item.get("metadata"), dict)
        and item["metadata"].get("version") == f"v{version}"
        and EXPECTED_CREATOR
        in {
            str(creator.get("name", ""))
            for creator in item["metadata"].get("creators", [])
            if isinstance(creator, dict)
        }
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one public Zenodo record for {version}, found {len(matches)}"
        )
    report = validate_record(matches[0], expected_tag_commit=tag_commit)
    report["verified_at"] = datetime.now(timezone.utc).isoformat()
    report["anonymous_verification"] = not bool(os.environ.get("GITHUB_TOKEN"))
    report["zenodo_api_authentication"] = "anonymous"
    report["github_api_authentication"] = (
        "token" if os.environ.get("GITHUB_TOKEN") else "anonymous"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=EXPECTED_VERSION)
    parser.add_argument(
        "--record-id",
        type=int,
        help="Verify a known public Zenodo record directly instead of search discovery.",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write verified evidence to {DEFAULT_REPORT.relative_to(REPO_ROOT)}.",
    )
    args = parser.parse_args()
    report = verify_zenodo(version=args.version, record_id=args.record_id)
    if args.write_report:
        DEFAULT_REPORT.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
