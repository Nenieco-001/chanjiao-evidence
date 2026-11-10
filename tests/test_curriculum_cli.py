import csv
import hashlib
import json
from pathlib import Path

from chanjiao_evidence.cli import main

ROOT = Path(__file__).resolve().parents[1]


def command(destination, plan=None):
    return [
        "curriculum",
        "--plan",
        str(plan or ROOT / "data/curricula/official-cs-extract.json"),
        "--scenario",
        str(ROOT / "data/examples/curriculum-scenario.json"),
        "--output",
        str(destination),
    ]


def test_actual_curriculum_normal_entry_and_manifest(tmp_path, capsys):
    output = tmp_path / "review"
    assert main(command(output)) == 0
    report = json.loads((output / "curriculum-review.json").read_text(encoding="utf-8"))
    assert report["curriculum"]["school"] == "中央财经大学"
    assert report["selected_candidate_id"] == "unchanged"
    assert report["employment_effect"]["status"] == "unidentified"
    assert [row["status"] for row in report["candidates"]] == ["feasible", "feasible", "infeasible"]
    feasible = report["candidates"][1]
    assert feasible["totals"]["hours_before"] == feasible["totals"]["hours_after"] == 384
    assert feasible["totals"]["credits_before"] == feasible["totals"]["credits_after"] == 24
    with (output / "course-actions.csv").open(encoding="utf-8-sig", newline="") as stream:
        actions = list(csv.DictReader(stream))
    practice = next(
        row
        for row in actions
        if row["candidate_id"] == "transfer_1" and row["course_id"] == "0630137"
    )
    assert practice["hours_before"] == "32" and practice["hours_after"] == "48"
    assert "review.md" in capsys.readouterr().out
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    for filename, digest in manifest["outputs"].items():
        assert hashlib.sha256((output / filename).read_bytes()).hexdigest() == digest
    assert "教师" in (output / "review.md").read_text(encoding="utf-8")


def test_course_review_is_deterministic(tmp_path):
    assert main(command(tmp_path / "a")) == 0
    assert main(command(tmp_path / "b")) == 0
    for name in ["curriculum-review.json", "course-actions.csv", "review.md", "manifest.json"]:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_course_review_keeps_existing_output(tmp_path):
    output = tmp_path / "review"
    output.mkdir()
    (output / "keep").write_text("original")
    assert main(command(output)) == 2
    assert (output / "keep").read_text() == "original"


def test_missing_hours_remains_unknown_in_output(tmp_path):
    plan = json.loads(
        (ROOT / "data/curricula/official-cs-extract.json").read_text(encoding="utf-8")
    )
    next(row for row in plan["courses"] if row["course_id"] == "0630137")["hours"] = None
    source = tmp_path / "missing.json"
    source.write_text(json.dumps(plan), encoding="utf-8")
    output = tmp_path / "review"
    assert main(command(output, source)) == 0
    report = json.loads((output / "curriculum-review.json").read_text(encoding="utf-8"))
    assert all(row["status"] == "not_evaluable" for row in report["candidates"])
    assert report["employment_effect"]["status"] == "unidentified"
