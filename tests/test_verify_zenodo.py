from __future__ import annotations

import pytest

from scripts import verify_zenodo as zenodo
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
            "version": "v1.2.1",
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
    assert report["version"] == "v1.2.1"
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
        (("metadata", "version", "v1.2.0"), "version"),
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


def test_verify_zenodo_can_retrieve_a_known_public_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, object] | None]] = []

    def fake_get_json(
        url: str,
        *,
        params: dict[str, object] | None = None,
    ) -> dict[str, object]:
        calls.append((url, params))
        assert url == "https://zenodo.org/api/records/12345678"
        assert params is None
        return _record()

    monkeypatch.setattr(zenodo, "_get_json", fake_get_json)
    monkeypatch.setattr(zenodo, "_resolve_annotated_tag", lambda version: TAG_COMMIT)

    report = zenodo.verify_zenodo(version="1.2.1", record_id=12345678)

    assert report["record_id"] == 12345678
    assert report["version"] == "v1.2.1"
    assert calls == [("https://zenodo.org/api/records/12345678", None)]


def test_get_json_scopes_github_token_to_github_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, dict[str, str]]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, bool]:
            return {"ok": True}

    def fake_get(
        url: str,
        *,
        params: dict[str, object] | None,
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        assert params is None
        assert timeout == 60
        captured.append((url, headers))
        return FakeResponse()

    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(zenodo.requests, "get", fake_get)

    zenodo._get_json(f"{zenodo.GITHUB_API}/git/ref/tags/v1.2.1")
    zenodo._get_json(f"{zenodo.ZENODO_RECORDS_API}/12345678")

    assert captured[0][1]["Authorization"] == "Bearer test-token"
    assert "Authorization" not in captured[1][1]
