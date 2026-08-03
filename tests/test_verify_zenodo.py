from __future__ import annotations

import pytest

from scripts.verify_zenodo import validate_record

TAG_COMMIT = "a" * 40


def _record() -> dict[str, object]:
    return {
        "id": 12345678,
        "doi": "10.5281/zenodo.12345678",
        "conceptdoi": "10.5281/zenodo.12345677",
        "created": "2026-08-03T10:00:00+00:00",
        "links": {
            "html": "https://zenodo.org/records/12345678",
        },
        "metadata": {
            "title": "FormosaNLU-Synth v1.2.1",
            "version": "1.2.1",
            "publication_date": "2026-08-03",
            "resource_type": {"id": "software", "title": "Software"},
            "creators": [{"name": "kuotunyu"}],
            "related_identifiers": [
                {
                    "identifier": (
                        "https://github.com/kuotunyu/FormosaNLU-Synth/"
                        "releases/tag/v1.2.1"
                    ),
                    "relation": "isSupplementTo",
                    "scheme": "url",
                }
            ],
        },
        "files": [
            {
                "key": "kuotunyu-FormosaNLU-Synth-v1.2.1.zip",
                "size": 1234,
                "checksum": "md5:0123456789abcdef0123456789abcdef",
            }
        ],
    }


def test_validate_record_accepts_exact_public_software_archive() -> None:
    report = validate_record(_record(), expected_tag_commit=TAG_COMMIT)

    assert report["status"] == "public_verified"
    assert report["doi"] == "10.5281/zenodo.12345678"
    assert report["concept_doi"] == "10.5281/zenodo.12345677"
    assert report["record_id"] == 12345678
    assert report["github_tag_commit"] == TAG_COMMIT
    assert report["files"] == [
        {
            "checksum": "md5:0123456789abcdef0123456789abcdef",
            "key": "kuotunyu-FormosaNLU-Synth-v1.2.1.zip",
            "size": 1234,
        }
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (("metadata", "version", "1.2.0"), "version"),
        (("metadata", "resource_type", {"id": "dataset"}), "software"),
        (("metadata", "creators", [{"name": "someone-else"}]), "creator"),
        (("doi", None, "10.9999/example.1"), "DOI"),
    ],
)
def test_validate_record_rejects_wrong_publication_identity(
    mutation: tuple[str, str | None, object],
    message: str,
) -> None:
    record = _record()
    outer, inner, value = mutation
    if inner is None:
        record[outer] = value
    else:
        nested = record[outer]
        assert isinstance(nested, dict)
        nested[inner] = value

    with pytest.raises(ValueError, match=message):
        validate_record(record, expected_tag_commit=TAG_COMMIT)


def test_validate_record_rejects_unrelated_repository() -> None:
    record = _record()
    metadata = record["metadata"]
    assert isinstance(metadata, dict)
    metadata["related_identifiers"] = [
        {
            "identifier": "https://github.com/another-owner/another-repo",
            "relation": "isSupplementTo",
            "scheme": "url",
        }
    ]

    with pytest.raises(ValueError, match="repository"):
        validate_record(record, expected_tag_commit=TAG_COMMIT)


def test_validate_record_requires_archive_file_metadata() -> None:
    record = _record()
    record["files"] = []

    with pytest.raises(ValueError, match="archive files"):
        validate_record(record, expected_tag_commit=TAG_COMMIT)
