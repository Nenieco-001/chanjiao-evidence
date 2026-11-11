import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from chanjiao_evidence.hard_materials import evaluate_hard_materials

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    paths = {
        "plan": "data/curricula/official-cs-extract.json",
        "program": "data/curricula/cufe-2025-program.json",
        "policy": "data/examples/program-policy.json",
        "demand": "data/examples/demand-beijing-2026.json",
        "comparison": "data/examples/comparison-assumptions.json",
        "evidence": "data/evidence/course-projects.json",
        "effects": "data/examples/project-effect-scenarios.json",
        "actions": "data/examples/hard-materials-actions.json",
    }
    return {name: json.loads((ROOT / path).read_bytes()) for name, path in paths.items()}


def test_real_inputs_produce_auditable_actions_and_three_path_checks(inputs):
    before = copy.deepcopy(inputs)
    result = evaluate_hard_materials(**inputs)
    merged = next(row for row in result["course_candidates"] if row["candidate_id"] == "merge_core")
    assert merged["status"] == "valid"
    assert merged["approval_status"] == "pending_school_review"
    assert merged["net_credit_delta"] == merged["net_hour_delta"] == 0
    assert [row["total_credits_after"] for row in merged["student_paths"]] == [147, 147, 148]
    assert all(row["status"] == "valid" for row in merged["student_paths"])
    assert all(len(row["module_credits_after"]) == 10 for row in merged["student_paths"])
    assert [row["action_type"] for row in merged["course_changes"]] == ["delete", "delete", "add"]
    assert [row["title"] for row in merged["course_changes"]] == [
        "软件工程",
        "专业综合实践",
        "软件工程与综合项目实践（拟设）",
    ]
    valid_adjustment = next(
        row
        for row in result["course_candidates"]
        if row["scenario_id"] == "within_core" and row["kind"] != "baseline"
    )
    assert valid_adjustment["status"] == "valid"
    assert [row["hours_after"] for row in valid_adjustment["course_changes"]] == [32, 48]
    assert result["selected_candidate_id"] == "unchanged"
    assert inputs == before


def test_original_cross_module_failure_and_unselected_donor_are_retained(inputs):
    result = evaluate_hard_materials(**inputs)
    candidate = next(
        row
        for row in result["course_candidates"]
        if row["scenario_id"] == "cross_module"
        and row["kind"] != "baseline"
        and row["added_hours"] == 16
    )
    assert candidate["status"] == "invalid"
    assert "module_minimum:professional_advanced" in candidate["student_paths"][0]["violations"]
    assert any(
        "donor_not_selected" in value for value in candidate["student_paths"][1]["violations"]
    )


@pytest.mark.parametrize("field,value", [("credits", 6), ("hours", 96)])
def test_nonconserving_merger_is_retained_as_invalid(inputs, field, value):
    inputs["actions"]["merges"][0]["proposed_course"][field] = value
    result = evaluate_hard_materials(**inputs)
    candidate = result["course_candidates"][-1]
    assert candidate["status"] == "invalid"
    assert field + "_conservation" in candidate["violations"]


def test_merger_cannot_move_credits_across_module_floors(inputs):
    inputs["actions"]["merges"][0]["proposed_course"]["module_id"] = "professional_advanced"
    result = evaluate_hard_materials(**inputs)
    candidate = result["course_candidates"][-1]
    assert candidate["status"] == "invalid"
    assert all(
        "module_minimum:professional_core" in row["violations"]
        for row in candidate["student_paths"]
    )


def test_merger_requires_source_courses_on_each_path(inputs):
    inputs["policy"]["student_paths"][0]["selected_course_ids"].remove("0610110")
    candidate = evaluate_hard_materials(**inputs)["course_candidates"][-1]
    assert candidate["status"] == "invalid"
    assert "source_not_selected:0610110" in candidate["student_paths"][0]["violations"]


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate_source",
        "unknown_source",
        "existing_target",
        "negative_hours",
        "nan_credits",
        "missing_risk_control",
    ],
)
def test_invalid_action_inputs_have_field_errors(inputs, kind):
    merge = inputs["actions"]["merges"][0]
    if kind == "duplicate_source":
        merge["source_course_ids"].append("0610110")
    elif kind == "unknown_source":
        merge["source_course_ids"][0] = "unknown"
    elif kind == "existing_target":
        merge["proposed_course"]["course_id"] = "0610110"
    elif kind == "negative_hours":
        merge["proposed_course"]["hours"] = -1
    elif kind == "nan_credits":
        merge["proposed_course"]["credits"] = float("nan")
    else:
        del inputs["actions"]["risk_controls"]["module_floor"]
    with pytest.raises(ValueError, match="actions"):
        evaluate_hard_materials(**inputs)


def test_missing_published_hours_keeps_merger_not_evaluable(inputs):
    next(row for row in inputs["program"]["courses"] if row["course_id"] == "0610110")["hours"] = (
        None
    )
    candidate = evaluate_hard_materials(**inputs)["course_candidates"][-1]
    assert candidate["status"] == "not_evaluable"
    assert "0610110.hours" in candidate["missing_inputs"]


def test_skill_carriers_resolve_to_real_names_and_keep_the_proxy_denominator(inputs):
    result = evaluate_hard_materials(**inputs)
    assert result["supply_demand"]["skills"]["mention_denominator"] == 256
    assert result["supply_demand"]["skills"]["baseline_coverage_interval"][0] == pytest.approx(
        111 / 256
    )
    java = next(row for row in result["skill_carriers"] if row["skill"] == "Java")
    assert java["title"] == "Java程序设计（全英语）"
    sql = next(row for row in result["skill_carriers"] if row["skill"] == "SQL")
    assert sql["title"] == "数据库系统"
    assert sql["evidence_kind"] == "proposed_content"


def test_risks_and_effects_keep_unknowns_and_official_scenario_method(inputs):
    result = evaluate_hard_materials(**inputs)
    assert len(result["risks"]) == 5
    assert all(row["probability_status"] == "unknown" for row in result["risks"])
    assert all(row["timing"] and row["threshold"] and row["owner"] for row in result["risks"])
    assert result["effects"]["target_effect"]["status"] == "unidentified"
    assert [row["estimate"] for row in result["effects"]["scenarios"]] == [-0.03, 0, 0.058]
    assert result["task_status"] == {"T1": "PARTIAL", "T2": "PARTIAL", "T3": "PASS", "T4": "PASS"}
    assert result["admissions"]["recommended_enrollment"] is None


def test_conflicting_course_names_have_a_source_error(inputs):
    inputs["plan"]["courses"][0]["title"] = "与原文不符的名称"
    with pytest.raises(ValueError, match="课程事实不一致"):
        evaluate_hard_materials(**inputs)


def test_path_name_lower_bounds_use_selected_courses_and_the_same_denominator(inputs):
    rows = evaluate_hard_materials(**inputs)["path_name_match_lower_bounds"]
    assert [row["matched_weight"] for row in rows] == [56, 111, 111]
    assert all(row["mention_denominator"] == 256 for row in rows)
    assert rows[0]["lower_bound"] == 56 / 256
    assert "Java" not in rows[0]["matched_skills"]


@pytest.fixture
def entry():
    path = ROOT / "analysis/competition/hard_materials.py"
    spec = importlib.util.spec_from_file_location("hard_materials_entry", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normal_generation_is_deterministic_and_hashes_exact_input_bytes(entry, tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    entry.generate(ROOT, left)
    entry.generate(ROOT, right)
    contents = {path.name: path.read_bytes() for path in left.iterdir()}
    assert contents == {path.name: path.read_bytes() for path in right.iterdir()}
    assert len(contents) == 6
    manifest = json.loads(contents["manifest.json"])
    for role, name in manifest["input_paths"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == manifest["inputs"][role]
    for name, value in manifest["outputs"].items():
        assert hashlib.sha256(contents[name]).hexdigest() == value
    with pytest.raises(FileExistsError, match="已存在"):
        entry.generate(ROOT, left)
    assert contents == {path.name: path.read_bytes() for path in left.iterdir()}


def test_publication_failure_cleans_its_own_temporary_directory(entry, tmp_path, monkeypatch):
    def fail(source, destination):
        raise OSError("synthetic publication failure")

    monkeypatch.setattr(entry, "_rename_with_retry", fail)
    with pytest.raises(OSError, match="synthetic"):
        entry.generate(ROOT, tmp_path / "failed")
    assert not list(tmp_path.iterdir())
