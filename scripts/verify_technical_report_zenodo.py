"""Verify the public Zenodo Technical note and its immutable file set."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
ZENODO_RECORDS_API = "https://zenodo.org/api/records"
EXPECTED_RECORD_ID = 21879155
EXPECTED_DOI = "10.5281/zenodo.21879155"
EXPECTED_SOFTWARE_DOI = "10.5281/zenodo.21879133"
EXPECTED_TITLE = (
    "FormosaNLU-Synth: Filtered Synthetic Data Distillation for Traditional "
    "Chinese (Taiwan) Natural Language Understanding"
)
EXPECTED_CREATOR = "kuotunyu"
EXPECTED_RESOURCE_TYPE = "publication-technicalnote"
EXPECTED_VERSION = "1.0.0"
EXPECTED_PUBLICATION_DATE = "2026-08-10"
EXPECTED_LICENSE = "cc-by-4.0"
EXPECTED_LANGUAGE = "eng"
LOCAL_FILES = (
    REPO_ROOT / "paper" / "formosanlu_synth.pdf",
    REPO_ROOT / "paper" / "formosanlu_synth.tex",
    REPO_ROOT / "paper" / "references.bib",
)
DEFAULT_REPORT = REPO_ROOT / "reports" / "v122_technical_report_zenodo.json"


def _get_json(url: str) -> dict[str, Any]:
    response = requests.get(
        url,
        headers={
            "Accept": "application/vnd.inveniordm.v1+json",
            "User-Agent": "FormosaNLU-Synth",
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Zenodo technical report response is not an object")
    return payload


def _get_bytes(url: str) -> bytes:
    response = requests.get(
        url,
        headers={
            "Accept": "*/*",
            "User-Agent": "FormosaNLU-Synth",
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.content


def _expected_local_files() -> dict[str, dict[str, object]]:
    expected: dict[str, dict[str, object]] = {}
    for path in LOCAL_FILES:
        content = path.read_bytes()
        expected[path.name] = {
            "checksum": f"md5:{hashlib.md5(content).hexdigest()}",
            "size": len(content),
        }
    return expected


def _creator_names(metadata: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for creator in metadata.get("creators", []):
        if not isinstance(creator, dict):
            continue
        person_or_org = creator.get("person_or_org", {})
        if isinstance(person_or_org, dict):
            names.append(str(person_or_org.get("name", "")))
    return names


def validate_record(
    payload: dict[str, Any],
    *,
    expected_files: dict[str, dict[str, object]],
) -> dict[str, Any]:
    """Validate one InvenioRDM v1 record and return normalized evidence."""
    record_id = int(payload.get("id", 0) or 0)
    if record_id != EXPECTED_RECORD_ID:
        raise ValueError(f"Unexpected Zenodo record ID: {record_id}")

    access = payload.get("access", {})
    if not isinstance(access, dict) or {
        str(access.get("record", "")),
        str(access.get("files", "")),
    } != {"public"}:
        raise ValueError("Zenodo technical report is not fully public")

    pids = payload.get("pids", {})
    doi_payload = pids.get("doi", {}) if isinstance(pids, dict) else {}
    doi = str(doi_payload.get("identifier", "")) if isinstance(doi_payload, dict) else ""
    if doi != EXPECTED_DOI:
        raise ValueError(f"Unexpected Zenodo technical report DOI: {doi!r}")

    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("Zenodo technical report metadata is missing")
    resource_type = metadata.get("resource_type", {})
    resource_type_id = (
        str(resource_type.get("id", "")) if isinstance(resource_type, dict) else ""
    )
    if resource_type_id != EXPECTED_RESOURCE_TYPE:
        raise ValueError(f"Unexpected technical report resource type: {resource_type_id!r}")

    creator_names = _creator_names(metadata)
    if creator_names != [EXPECTED_CREATOR]:
        raise ValueError(f"Unexpected technical report creator metadata: {creator_names}")
    if str(metadata.get("title", "")) != EXPECTED_TITLE:
        raise ValueError("Unexpected technical report title")
    if str(metadata.get("version", "")) != EXPECTED_VERSION:
        raise ValueError("Unexpected technical report version")
    if str(metadata.get("publication_date", "")) != EXPECTED_PUBLICATION_DATE:
        raise ValueError("Unexpected technical report publication date")

    rights = metadata.get("rights", [])
    right_ids = [
        str(item.get("id", "")) for item in rights if isinstance(item, dict)
    ]
    if right_ids != [EXPECTED_LICENSE]:
        raise ValueError(f"Unexpected technical report license: {right_ids}")
    languages = metadata.get("languages", [])
    language_ids = [
        str(item.get("id", "")) for item in languages if isinstance(item, dict)
    ]
    if language_ids != [EXPECTED_LANGUAGE]:
        raise ValueError(f"Unexpected technical report language: {language_ids}")
    if "has not undergone peer review" not in str(metadata.get("description", "")).lower():
        raise ValueError("Technical report peer review limitation is missing")

    related = metadata.get("related_identifiers", [])
    software_links = [
        item
        for item in related
        if isinstance(item, dict)
        and str(item.get("identifier", "")) == EXPECTED_SOFTWARE_DOI
        and str(item.get("scheme", "")) == "doi"
        and isinstance(item.get("relation_type"), dict)
        and str(item["relation_type"].get("id", "")) == "documents"
        and isinstance(item.get("resource_type"), dict)
        and str(item["resource_type"].get("id", "")) == "software"
    ]
    if len(software_links) != 1:
        raise ValueError("Technical report does not document the expected software DOI")

    custom_fields = payload.get("custom_fields", {})
    imprint = (
        custom_fields.get("imprint:imprint", {})
        if isinstance(custom_fields, dict)
        else {}
    )
    expected_imprint = {
        "title": "FormosaNLU-Synth Technical Report",
        "pages": "6",
        "place": "Taipei, Taiwan",
    }
    if not isinstance(imprint, dict) or {
        key: str(imprint.get(key, "")) for key in expected_imprint
    } != expected_imprint:
        raise ValueError("Unexpected technical report imprint metadata")

    files_payload = payload.get("files", {})
    entries = files_payload.get("entries", {}) if isinstance(files_payload, dict) else {}
    if not isinstance(entries, dict) or set(entries) != set(expected_files):
        raise ValueError("Unexpected technical report file allowlist")
    files: list[dict[str, object]] = []
    for key in sorted(expected_files):
        entry = entries.get(key, {})
        expected = expected_files[key]
        if not isinstance(entry, dict) or (
            str(entry.get("key", "")) != key
            or str(entry.get("checksum", "")) != str(expected["checksum"])
            or int(entry.get("size", 0) or 0) != int(expected["size"])
        ):
            raise ValueError(f"Unexpected technical report file metadata: {key}")
        files.append(
            {
                "checksum": str(entry["checksum"]),
                "key": key,
                "size": int(entry["size"]),
            }
        )

    links = payload.get("links", {})
    record_url = (
        str(links.get("self_html", "")) if isinstance(links, dict) else ""
    ) or f"https://zenodo.org/records/{record_id}"
    return {
        "schema_version": 1,
        "status": "public_verified",
        "record_id": record_id,
        "record_url": record_url,
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}",
        "title": EXPECTED_TITLE,
        "version": EXPECTED_VERSION,
        "publication_date": EXPECTED_PUBLICATION_DATE,
        "creator_names": creator_names,
        "resource_type": resource_type_id,
        "license": EXPECTED_LICENSE,
        "language": EXPECTED_LANGUAGE,
        "related_software_doi": EXPECTED_SOFTWARE_DOI,
        "files": files,
    }


def verify_technical_report() -> dict[str, Any]:
    """Verify public metadata plus freshly downloaded file bytes anonymously."""
    payload = _get_json(f"{ZENODO_RECORDS_API}/{EXPECTED_RECORD_ID}")
    expected_files = _expected_local_files()
    report = validate_record(payload, expected_files=expected_files)

    files_payload = payload["files"]
    assert isinstance(files_payload, dict)
    entries = files_payload["entries"]
    assert isinstance(entries, dict)
    for key in sorted(expected_files):
        entry = entries[key]
        assert isinstance(entry, dict)
        links = entry.get("links", {})
        if not isinstance(links, dict) or not links.get("content"):
            raise ValueError(f"Technical report content link is missing: {key}")
        content = _get_bytes(str(links["content"]))
        observed = {
            "checksum": f"md5:{hashlib.md5(content).hexdigest()}",
            "size": len(content),
        }
        if observed != expected_files[key]:
            raise ValueError(f"Downloaded technical report file mismatch: {key}")

    report.update(
        {
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "anonymous_verification": True,
            "downloads_verified": True,
            "zenodo_api_authentication": "anonymous",
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write verified evidence to {DEFAULT_REPORT.relative_to(REPO_ROOT)}.",
    )
    args = parser.parse_args()
    report = verify_technical_report()
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
