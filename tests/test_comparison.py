import copy
import json
from pathlib import Path

import pytest

from chanjiao_evidence.comparison import compare_supply_demand


@pytest.fixture
def inputs():
    return (
        json.loads(Path("data/curricula/cufe-2025-program.json").read_text(encoding="utf-8")),
        {
            "schema_version": 1,
            "evidence_mode": "historical_sample",
            "scope": "合成小样本用于函数测试",
            "source": "测试构造",
            "job_records": 10,
            "skill_counts": {"Python": 6, "SQL": 4},
            "job_family_counts": {"software": 7, "data": 3},
        },
        {
            "schema_version": 1,
            "evidence_mode": "scenario_assumptions",
            "skill_links": [
                {"skill": "Python", "course_id": "0630158", "source_location": "公开课程名称"}
            ],
            "planned_skills": ["SQL"],
            "proposed_direction_shares": {"software": 0.6, "data": 0.4},
            "baseline_direction_hypotheses": [
                {"scenario_id": "already_aligned", "shares": {"software": 0.7, "data": 0.3}},
                {"scenario_id": "unbalanced", "shares": {"software": 1.0, "data": 0.0}},
            ],
            "scale_scenarios": [
                {
                    "scenario_id": "low_access",
                    "cohort_index": 10,
                    "jobseeker_fraction": 0.8,
                    "sample_access_share": 0.1,
                    "positions_per_record": 1,
                },
                {
                    "scenario_id": "high_access",
                    "cohort_index": 10,
                    "jobseeker_fraction": 0.8,
                    "sample_access_share": 1.0,
                    "positions_per_record": 1,
                },
            ],
            "assumption_source": "全部是假设，用于核对公式，尚未在学校校准",
        },
    )


def test_partial_skill_evidence_retains_unknown_bounds_and_zero_gain(inputs):
    result = compare_supply_demand(*inputs)
    assert result["skills"]["baseline_coverage_interval"] == pytest.approx([0.6, 1])
    assert result["skills"]["proposed_coverage_interval"] == pytest.approx([1, 1])
    assert result["skills"]["proxy_gain_interval"] == pytest.approx([0, 0.4])
    assert result["skills"]["unknown_skills"] == ["SQL"]
    assert result["student_mastery_effect"] == "unidentified"


def test_directions_preserve_worse_than_baseline_and_improvement(inputs):
    result = compare_supply_demand(*inputs)
    a, b = result["directions"]["conditional_comparisons"]
    assert a["improvement"] == pytest.approx(-0.1)
    assert b["improvement"] == pytest.approx(0.2)
    assert result["directions"]["observed_school_gap"] is None


def test_scale_uses_normalized_index_and_preserves_negative_results(inputs):
    result = compare_supply_demand(*inputs)
    a, b = result["scale"]["conditional_scenarios"]
    assert a["opportunity_minus_jobseekers"] == pytest.approx(-7)
    assert b["opportunity_minus_jobseekers"] == pytest.approx(2)
    assert a["break_even_sample_access_share"] == pytest.approx(0.8)
    assert result["scale"]["actual_school_gap"] is None


def test_no_skill_mentions_and_zero_jobs_are_explicit(inputs):
    program, demand, config = inputs
    demand.update(
        job_records=0,
        skill_counts={"Python": 0, "SQL": 0},
        job_family_counts={"software": 0, "data": 0},
    )
    result = compare_supply_demand(program, demand, config)
    assert result["skills"]["baseline_coverage_interval"] is None
    assert result["directions"]["conditional_comparisons"] == []
    assert all(
        row["break_even_sample_access_share"] is None
        for row in result["scale"]["conditional_scenarios"]
    )


@pytest.mark.parametrize(
    "key,value",
    [
        ("job_records", True),
        ("job_records", -1),
        ("job_records", 10**400),
        ("skill_counts", {"SQL": 11}),
        ("job_family_counts", {"software": 9}),
    ],
)
def test_invalid_demand_is_rejected(inputs, key, value):
    program, demand, config = inputs
    demand[key] = value
    with pytest.raises(ValueError):
        compare_supply_demand(program, demand, config)


@pytest.mark.parametrize(
    "change",
    [
        lambda c: c["proposed_direction_shares"].update(software=0.9),
        lambda c: c["scale_scenarios"][0].update(sample_access_share=2),
        lambda c: c["skill_links"][0].update(course_id="unknown"),
        lambda c: c["planned_skills"].append("unknown"),
        lambda c: c.update(assumption_source=""),
    ],
)
def test_invalid_assumptions_are_rejected(inputs, change):
    program, demand, config = inputs
    change(config)
    with pytest.raises(ValueError):
        compare_supply_demand(program, demand, config)


def test_inputs_are_unchanged_and_results_repeat(inputs):
    before = copy.deepcopy(inputs)
    assert compare_supply_demand(*inputs) == compare_supply_demand(*inputs)
    assert inputs == before


@pytest.mark.parametrize("kind", ["product", "threshold"])
def test_scale_arithmetic_overflow_is_a_field_error(inputs, kind):
    program, demand, config = inputs
    row = config["scale_scenarios"][0]
    if kind == "product":
        row["positions_per_record"] = 10**308
    else:
        row.update(cohort_index=1e308, positions_per_record=1e-308)
    with pytest.raises(ValueError, match="scale_scenarios"):
        compare_supply_demand(program, demand, config)


def test_invalid_program_course_identifier_is_field_error(inputs):
    program, demand, config = inputs
    program["courses"][0]["course_id"] = []
    with pytest.raises(ValueError, match="course_id"):
        compare_supply_demand(program, demand, config)
