from __future__ import annotations

from scripts.verify_reproduce import documented_modules, verify


def test_extracts_module_targets_in_first_seen_order_without_duplicates() -> None:
    readme = """
```bash
python -m scripts.check_env
python -m src.data.freeze_split
python -m src.data.freeze_split --verify
python -m scripts.check_env
```
"""
    assert documented_modules(readme) == ["scripts.check_env", "src.data.freeze_split"]


def test_ignores_non_module_commands() -> None:
    """uv and git lines are instructions too, but they are not entry points."""
    readme = """
```bash
uv sync --extra demo
git clone https://example.com/repo
python -m scripts.check_env
```
"""
    assert documented_modules(readme) == ["scripts.check_env"]


def test_a_renamed_module_is_reported_as_broken(monkeypatch) -> None:
    """The failure this exists to catch: README still names a module that moved."""
    import scripts.verify_reproduce as module

    def fake_check(name: str, **_: object) -> dict:
        ok = name != "scripts.renamed_away"
        return {"module": name, "ok": ok, "returncode": 0 if ok else 1, "detail": ""}

    monkeypatch.setattr(module, "check_module", fake_check)

    report = verify(
        "```bash\npython -m scripts.check_env\npython -m scripts.renamed_away\n```"
    )

    assert report["status"] == "broken"
    assert report["failed"] == ["scripts.renamed_away"]


def test_all_passing_reports_ok(monkeypatch) -> None:
    import scripts.verify_reproduce as module

    monkeypatch.setattr(
        module,
        "check_module",
        lambda name, **_: {"module": name, "ok": True, "returncode": 0, "detail": ""},
    )

    report = verify("```bash\npython -m scripts.check_env\n```")
    assert report["status"] == "ok"
    assert report["failed"] == []
    assert report["documented_modules"] == 1
