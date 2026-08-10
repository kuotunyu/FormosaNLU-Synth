from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

EXPECTED_FILES = {
    "formosanlu_synth.pdf": {
        "checksum": "md5:525864c3318f5de28242b89a9dc4e285",
        "size": 65163,
    },
    "formosanlu_synth.tex": {
        "checksum": "md5:059fbf16c13a353ba3caba09a6790712",
        "size": 16593,
    },
    "references.bib": {
        "checksum": "md5:f7a9161247f4659f730175b1101df298",
        "size": 2756,
    },
}


def _record() -> dict[str, object]:
    return {
        "id": "21879155",
        "access": {"record": "public", "files": "public"},
        "pids": {
            "doi": {
                "identifier": "10.5281/zenodo.21879155",
                "provider": "datacite",
            }
        },
        "links": {
            "self_html": "https://zenodo.org/records/21879155",
            "doi": "https://doi.org/10.5281/zenodo.21879155",
        },
        "metadata": {
            "resource_type": {"id": "publication-technicalnote"},
            "creators": [
                {
                    "person_or_org": {
                        "type": "personal",
                        "name": "kuotunyu",
                        "family_name": "kuotunyu",
                    }
                }
            ],
            "title": (
                "FormosaNLU-Synth: Filtered Synthetic Data Distillation for "
                "Traditional Chinese (Taiwan) Natural Language Understanding"
            ),
            "publisher": "Zenodo",
            "publication_date": "2026-08-10",
            "languages": [{"id": "eng"}],
            "related_identifiers": [
                {
                    "identifier": "10.5281/zenodo.21879133",
                    "scheme": "doi",
                    "relation_type": {"id": "documents"},
                    "resource_type": {"id": "software"},
                }
            ],
            "version": "1.0.0",
            "rights": [{"id": "cc-by-4.0"}],
            "copyright": "Copyright (C) 2026 kuotunyu.",
            "description": (
                "<p>This archival technical note has not undergone peer review. "
                "The corresponding software release is archived at "
                "https://doi.org/10.5281/zenodo.21879133.</p>"
            ),
        },
        "custom_fields": {
            "imprint:imprint": {
                "title": "FormosaNLU-Synth Technical Report",
                "pages": "6",
                "place": "Taipei, Taiwan",
            }
        },
        "files": {
            "entries": {
                name: {
                    "key": name,
                    "checksum": details["checksum"],
                    "size": details["size"],
                    "links": {
                        "content": (
                            "https://zenodo.org/api/records/21879155/files/"
                            f"{name}/content"
                        )
                    },
                }
                for name, details in EXPECTED_FILES.items()
            }
        },
    }


def test_validate_record_accepts_exact_public_technical_note() -> None:
    from scripts.verify_technical_report_zenodo import validate_record

    report = validate_record(_record(), expected_files=EXPECTED_FILES)

    assert report["status"] == "public_verified"
    assert report["doi"] == "10.5281/zenodo.21879155"
    assert report["creator_names"] == ["kuotunyu"]
    assert report["resource_type"] == "publication-technicalnote"
    assert report["related_software_doi"] == "10.5281/zenodo.21879133"
    assert report["files"] == [
        {
            "checksum": EXPECTED_FILES[name]["checksum"],
            "key": name,
            "size": EXPECTED_FILES[name]["size"],
        }
        for name in sorted(EXPECTED_FILES)
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (("metadata", "resource_type", {"id": "software"}), "resource type"),
        (("metadata", "creators", []), "creator"),
        (("metadata", "rights", [{"id": "mit"}]), "license"),
        (("metadata", "languages", [{"id": "zho"}]), "language"),
        (("metadata", "description", "<p>Peer review status omitted.</p>"), "peer"),
    ],
)
def test_validate_record_rejects_identity_or_scope_drift(
    mutation: tuple[str, str, object],
    message: str,
) -> None:
    from scripts.verify_technical_report_zenodo import validate_record

    record = deepcopy(_record())
    outer, inner, value = mutation
    nested = record[outer]
    assert isinstance(nested, dict)
    nested[inner] = value

    with pytest.raises(ValueError, match=message):
        validate_record(record, expected_files=EXPECTED_FILES)


def test_validate_record_rejects_wrong_related_software_doi() -> None:
    from scripts.verify_technical_report_zenodo import validate_record

    record = deepcopy(_record())
    metadata = record["metadata"]
    assert isinstance(metadata, dict)
    related = metadata["related_identifiers"]
    assert isinstance(related, list)
    related[0]["identifier"] = "10.5281/zenodo.99999999"

    with pytest.raises(ValueError, match="software DOI"):
        validate_record(record, expected_files=EXPECTED_FILES)


def test_validate_record_rejects_file_allowlist_or_checksum_drift() -> None:
    from scripts.verify_technical_report_zenodo import validate_record

    record = deepcopy(_record())
    files = record["files"]
    assert isinstance(files, dict)
    entries = files["entries"]
    assert isinstance(entries, dict)
    pdf = entries["formosanlu_synth.pdf"]
    assert isinstance(pdf, dict)
    pdf["checksum"] = "md5:00000000000000000000000000000000"

    with pytest.raises(ValueError, match="file metadata"):
        validate_record(record, expected_files=EXPECTED_FILES)


def test_verify_technical_report_downloads_and_hashes_each_public_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import verify_technical_report_zenodo as verifier

    payload = deepcopy(_record())
    file_bytes = {
        "formosanlu_synth.pdf": b"pdf-evidence",
        "formosanlu_synth.tex": b"tex-evidence",
        "references.bib": b"bib-evidence",
    }
    expected_files = {
        name: {
            "checksum": f"md5:{hashlib.md5(content).hexdigest()}",
            "size": len(content),
        }
        for name, content in file_bytes.items()
    }
    files = payload["files"]
    assert isinstance(files, dict)
    entries = files["entries"]
    assert isinstance(entries, dict)
    for name, expected in expected_files.items():
        entry = entries[name]
        assert isinstance(entry, dict)
        entry.update(expected)

    calls: list[str] = []

    def fake_get_json(url: str) -> dict[str, object]:
        calls.append(url)
        return payload

    def fake_get_bytes(url: str) -> bytes:
        calls.append(url)
        name = url.rsplit("/", maxsplit=2)[-2]
        return file_bytes[name]

    monkeypatch.setattr(verifier, "_get_json", fake_get_json)
    monkeypatch.setattr(verifier, "_get_bytes", fake_get_bytes)
    monkeypatch.setattr(verifier, "_expected_local_files", lambda: expected_files)

    report = verifier.verify_technical_report()

    assert report["downloads_verified"] is True
    assert report["anonymous_verification"] is True
    assert calls == [
        "https://zenodo.org/api/records/21879155",
        *[
            (
                "https://zenodo.org/api/records/21879155/files/"
                f"{name}/content"
            )
            for name in sorted(file_bytes)
        ],
    ]


def test_get_bytes_uses_zenodo_compatible_wildcard_accept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import verify_technical_report_zenodo as verifier

    captured: dict[str, object] = {}

    class FakeResponse:
        content = b"verified-content"

        def raise_for_status(self) -> None:
            return None

    def fake_get(
        url: str,
        *,
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        captured.update(url=url, headers=headers, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr(verifier.requests, "get", fake_get)

    assert verifier._get_bytes("https://zenodo.org/content") == b"verified-content"
    assert captured["headers"] == {
        "Accept": "*/*",
        "User-Agent": "FormosaNLU-Synth",
    }
    assert captured["timeout"] == 60
