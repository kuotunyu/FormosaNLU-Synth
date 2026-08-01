"""Make the `requires_local_artifacts` marker actually skip when it must.

`data/`, `runs/` and `results/` are gitignored because they are reproducible
outputs, not sources. Tests that read them already carry the
`requires_local_artifacts` marker, but a marker only labels a test -- it does
not skip it. A plain `pytest` run in a fresh clone therefore failed six tests,
which tells someone who just cloned the repository that the project is broken
when in fact they have simply not run the pipeline yet.

Marked tests are now skipped, with a reason, when the corpus they need is
absent. Where the artifacts exist -- the maintainer's machine, or anyone who
has followed the reproduction steps -- they run exactly as before, so no
coverage is quietly lost.
"""

from __future__ import annotations

import pytest

from src.training.train import REPO_ROOT

# Presence of the raw corpus is the cheapest reliable signal that the pipeline
# has been run at all; every marked test needs something derived from it.
LOCAL_CORPUS = REPO_ROOT / "data" / "raw" / "massive"

SKIP_REASON = (
    "requires regenerable local artifacts (data/ is gitignored); "
    "run the README reproduction steps to produce them"
)


def local_artifacts_present() -> bool:
    return LOCAL_CORPUS.exists()


def pytest_collection_modifyitems(config, items) -> None:  # noqa: ARG001
    if local_artifacts_present():
        return
    skip = pytest.mark.skip(reason=SKIP_REASON)
    for item in items:
        if "requires_local_artifacts" in item.keywords:
            item.add_marker(skip)
