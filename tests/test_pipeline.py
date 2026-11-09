import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from chanjiao_evidence.pipeline import run


@pytest.fixture
def inputs(tmp_path, panel, metadata, plans):
    panel.to_csv(tmp_path / "panel.csv", index=False)
    for name, value in [("metadata", metadata), ("plans", plans)]:
        (tmp_path / f"{name}.json").write_text(json.dumps(value), encoding="utf-8")
    return [tmp_path / name for name in ["panel.csv", "metadata.json", "plans.json"]]


def test_normal_entry_point_writes_reproducible_manifest(tmp_path, inputs):
    first = run(*inputs, tmp_path / "first")
    second = run(*inputs, tmp_path / "second")
    assert first == second
    assert first["metadata"]["evidence_mode"] == "synthetic"
    assert first["analysis"]["main"]["estimate"] == pytest.approx(0.06)
    assert first["planning"]["selected_plan"] == "internship"
    assert first["limitations"]
    manifest = json.loads((tmp_path / "first" / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["inputs"]) == 3
    assert manifest["outputs"]["report.json"]
    assert manifest["source_sha256"]
    assert (tmp_path / "first" / "manifest.json").read_bytes() == (
        tmp_path / "second" / "manifest.json"
    ).read_bytes()


def test_existing_output_is_preserved(tmp_path, inputs):
    destination = tmp_path / "output"
    destination.mkdir()
    (destination / "keep").write_text("original")
    with pytest.raises(FileExistsError):
        run(*inputs, destination)
    assert (destination / "keep").read_text() == "original"


def test_mismatched_outcome_has_no_partial_artifact(tmp_path, inputs):
    plans = json.loads(inputs[2].read_text())
    plans["outcome_id"] = "earnings"
    inputs[2].write_text(json.dumps(plans))
    with pytest.raises(ValueError, match="outcome_id"):
        run(*inputs, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_mismatched_action_is_rejected(tmp_path, inputs):
    details = json.loads(inputs[1].read_text())
    details["action_id"] = "different_reform"
    inputs[1].write_text(json.dumps(details))
    with pytest.raises(ValueError, match="action_id"):
        run(*inputs, tmp_path / "output")


def test_cli_failure_and_success_exit_codes(tmp_path, inputs):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1] / "src"))
    command = [
        sys.executable,
        "-m",
        "chanjiao_evidence",
        "run",
        "--panel",
        str(inputs[0]),
        "--metadata",
        str(inputs[1]),
        "--plans",
        str(inputs[2]),
        "--output",
        str(tmp_path / "cli"),
    ]
    result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "cli" / "report.json").read_text(encoding="utf-8"))["analysis"]
    result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    assert result.returncode == 2
