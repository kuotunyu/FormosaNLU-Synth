import json
from pathlib import Path

import pytest

from scripts.prepare_colab_bundle import REQUIRED_ARTIFACTS, bundle_files

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_colab_notebook_is_clean_valid_python_wrapper() -> None:
    notebook = json.loads(
        (REPO_ROOT / "notebooks" / "01_sft_student.ipynb").read_text(
            encoding="utf-8"
        )
    )
    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["accelerator"] == "GPU"
    code = []
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        assert cell["execution_count"] is None
        assert cell["outputs"] == []
        source = "".join(cell["source"])
        compile(source, f"notebook-cell-{index}", "exec")
        code.append(source)
    joined = "\n".join(code)
    assert "src.training.train" in joined
    assert "'--resume'" in joined
    assert "stop_sync.wait(120)" in joined
    assert "userdata.get('HF_TOKEN')" in joined
    assert "M9-LOCAL-4090" not in joined


@pytest.mark.requires_local_artifacts
def test_colab_bundle_covers_every_local_training_artifact() -> None:
    members = set(bundle_files())
    assert set(REQUIRED_ARTIFACTS).issubset(members)
    assert Path("src/training/train.py") in members
    assert Path("configs/train.yaml") in members
    assert Path("uv.lock") in members
