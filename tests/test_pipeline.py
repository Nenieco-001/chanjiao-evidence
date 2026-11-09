import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from chanjiao_evidence.pipeline import run


def test_generates_chinese_reports_and_hashes_all_outputs(tmp_path, inputs):
    report = run(*inputs, tmp_path / "rich-report")
    assert report["trajectory"][0]["year"] == 2020
    assert report["trajectory"][0]["treated_mean"] == pytest.approx(0.39)
    assert report["evidence"]["status"] == "not_provided"
    output = tmp_path / "rich-report"
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["outputs"]) == {"report.json", "report.html", "report.md"}
    for name, expected in manifest["outputs"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
    assert "合成" in (output / "report.html").read_text(encoding="utf-8")


def test_evidence_is_hashed_but_never_changes_estimated_effect(tmp_path, inputs):
    from test_evidence import evidence_bytes

    evidence = tmp_path / "papers.json"
    evidence.write_bytes(evidence_bytes())
    baseline = run(*inputs, tmp_path / "without")
    contextual = run(*inputs, tmp_path / "with", evidence_path=evidence)
    assert contextual["analysis"] == baseline["analysis"]
    assert contextual["planning"] == baseline["planning"]
    assert contextual["evidence"]["cards"][0]["matches_target_outcome"] is False
    manifest = json.loads((tmp_path / "with" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["inputs"]["evidence"] == hashlib.sha256(evidence.read_bytes()).hexdigest()


def test_repeated_readable_reports_are_byte_identical(tmp_path, inputs):
    run(*inputs, tmp_path / "a")
    run(*inputs, tmp_path / "b")
    for name in ["report.html", "report.md", "report.json", "manifest.json"]:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


@pytest.mark.skipif(os.name != "nt", reason="Windows 共享/锁冲突重试")
def test_publish_retries_transient_windows_lock(tmp_path, inputs, monkeypatch):
    from chanjiao_evidence import pipeline

    real_rename = os.rename
    calls = []

    def flaky_rename(source, destination):
        calls.append(1)
        if len(calls) == 1:
            raise PermissionError(13, "temporarily locked", None, 5)
        return real_rename(source, destination)

    monkeypatch.setattr(pipeline.os, "rename", flaky_rename)
    run(*inputs, tmp_path / "output")
    assert 2 <= len(calls) <= pipeline._RENAME_ATTEMPTS
    assert (tmp_path / "output" / "report.json").exists()


def test_cli_accepts_literature_and_writes_readable_report(tmp_path, inputs):
    from test_evidence import evidence_bytes

    evidence = tmp_path / "papers.json"
    evidence.write_bytes(evidence_bytes())
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
        "--evidence",
        str(evidence),
        "--output",
        str(tmp_path / "readable"),
    ]
    completed = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert "report.html" in completed.stdout
    details = json.loads((tmp_path / "readable" / "report.json").read_text(encoding="utf-8"))
    assert details["evidence"]["used_for_estimation"] is False


def test_invalid_literature_leaves_no_artifact(tmp_path, inputs):
    evidence = tmp_path / "papers.json"
    evidence.write_bytes(b'{"schema_version": 1}')
    with pytest.raises(ValueError, match="cards"):
        run(*inputs, tmp_path / "invalid-papers", evidence_path=evidence)
    assert not (tmp_path / "invalid-papers").exists()


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


def test_manifest_input_hashes_match_input_bytes(tmp_path, inputs):
    run(*inputs, tmp_path / "output")
    manifest = json.loads((tmp_path / "output" / "manifest.json").read_text(encoding="utf-8"))
    for role, path in zip(["panel", "metadata", "plans"], inputs, strict=True):
        assert manifest["inputs"][role] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("content", [b"[]", b"null"])
def test_plans_json_must_be_object(tmp_path, inputs, content):
    inputs[2].write_bytes(content)
    with pytest.raises(ValueError, match="plans JSON must be an object"):
        run(*inputs, tmp_path / "output")
    assert not (tmp_path / "output").exists()


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
