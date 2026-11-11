"""Hand-checked policy fixtures are assumptions, never student observations."""

import copy
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def inputs():
    plan = json.loads(Path("data/curricula/official-cs-extract.json").read_text(encoding="utf-8"))
    scenario = json.loads(
        Path("data/examples/curriculum-scenario.json").read_text(encoding="utf-8")
    )
    scenario["hour_options"] = [16]
    revised = copy.deepcopy(scenario)
    revised.update(
        donor_course_id="0610110", minimum_hours={"0610110": 32}, minimum_credits={"0610110": 2}
    )
    modules = dict(
        general_electives=8,
        politics=21,
        foreign_languages=10,
        mathematics=17,
        sports=4,
        discipline_foundation=27,
        professional_core=25,
        professional_advanced=17,
        professional_extension=5,
        practical_components=13,
    )
    course_modules = {row["course_id"]: "professional_core" for row in plan["courses"]}
    course_modules["0610300"] = "professional_advanced"
    program = {
        "schema_version": 1,
        "evidence_mode": "published_program_requirements",
        "minimum_total_credits": 147,
        "module_minimum_credits": modules,
        "course_modules": course_modules,
    }
    ids = [row["course_id"] for row in plan["courses"]]
    paths = [
        {
            "path_id": "exact_with_donor",
            "module_credits": copy.deepcopy(modules),
            "selected_course_ids": ids,
        },
        {
            "path_id": "exact_without_donor",
            "module_credits": copy.deepcopy(modules),
            "selected_course_ids": [x for x in ids if x != "0610300"],
        },
        {
            "path_id": "advanced_surplus",
            "module_credits": dict(modules, professional_advanced=18),
            "selected_course_ids": ids,
        },
    ]
    config = {
        "schema_version": 1,
        "evidence_mode": "scenario_assumptions",
        "curriculum_scenarios": [
            {"scenario_id": "cross_module", "config": scenario},
            {"scenario_id": "within_core", "config": revised},
        ],
        "student_paths": paths,
        "selection_semester": 4,
        "directions": [
            {
                "direction_id": "software",
                "label": "软件方向假设",
                "job_family": "软件开发",
                "course_ids": ["0610110"],
                "capacity": 30,
                "minimum_score": 0.6,
            }
        ],
        "admissions": {
            "baseline_enrollment": None,
            "target_rate": 0.85,
            "gain": 1,
            "max_relative_change": 0.05,
            "minimum_enrollment": None,
            "maximum_enrollment": None,
            "feedback_lag_years": 4,
            "feedback_interval_years": 1,
            "observed_employment_rate": None,
            "observed_feedback_year": None,
        },
        "risks": [
            {
                "risk_id": name,
                "action_id": "cross_module",
                "probability_range": [0, 1],
                "impact": "测试影响",
                "owner": "教学委员会",
                "trigger": "测试阈值",
                "response": "暂停并复核",
            }
            for name in ["credits", "staff", "content"]
        ],
    }
    return plan, config, program


def evaluate(inputs):
    return importlib.import_module("chanjiao_evidence.strategy").evaluate_strategy(*inputs)


def test_cross_module_paths_reject_exact_and_unselected_donor_but_keep_surplus(inputs):
    result = evaluate(inputs)
    candidate = result["scenario_results"][0]["candidates"][1]
    first, absent, surplus = candidate["student_paths"]
    assert candidate["status"] == "invalid"
    assert first["module_credits_after"]["professional_core"] == 26
    assert first["module_credits_after"]["professional_advanced"] == 16
    assert first["violations"] == ["module_minimum:professional_advanced"]
    assert absent["status"] == "invalid"
    assert "donor_not_selected:0610300" in absent["violations"]
    assert surplus["status"] == "valid"
    assert surplus["total_credits_after"] == 148


def test_violation_triggers_actual_recalculation_with_revised_donor(inputs):
    result = evaluate(inputs)
    revised = result["scenario_results"][1]["candidates"][1]
    assert revised["course_changes"][0]["course_id"] == "0610110"
    assert revised["status"] == "valid"
    assert all(
        row["module_credits_after"]["professional_core"] == 25 for row in revised["student_paths"]
    )
    revision = [row for row in result["process_log"] if row["stage"] == "revision"][0]
    assert revision["triggered_by"]
    assert revision["next_scenario_id"] == "within_core"
    assert result["termination_reason"] == "modeled_constraints_satisfied"
    assert result["selected_candidate_id"] == "unchanged"


def test_exhausted_revision_keeps_failure_and_terminates(inputs):
    inputs[1]["curriculum_scenarios"].pop()
    result = evaluate(inputs)
    assert result["termination_reason"] == "revision_options_exhausted"
    assert result["scenario_results"][0]["candidates"][1]["status"] == "invalid"


def test_valid_first_scenario_does_not_claim_failure_triggered_revision(inputs):
    inputs[1]["curriculum_scenarios"] = [inputs[1]["curriculum_scenarios"][1]]
    for risk in inputs[1]["risks"]:
        risk["action_id"] = "within_core"
    result = evaluate(inputs)
    assert result["termination_reason"] == "modeled_constraints_satisfied"
    assert not [row for row in result["process_log"] if row["stage"] == "revision"]


def test_missing_scale_and_feedback_stay_unknown_and_assumptions_are_preserved(inputs):
    original = copy.deepcopy(inputs)
    result = evaluate(inputs)
    assert result["admissions"]["recommended_enrollment"] is None
    assert result["admissions"]["status"] == "awaiting_inputs"
    assert result["scenario_assumptions"] == inputs[1]
    assert result["unknowns"]
    assert result["direction_policy"]["status"] == "pending_review"
    assert result["direction_policy"]["selection_semester"] == 4
    assert result["direction_policy"]["assignments"] == []
    assert len(result["risk_matrix"]) == 3
    assert all(row["evidence_mode"] == "scenario_assumptions" for row in result["risk_matrix"])
    assert inputs == original
    assert evaluate(inputs) == result


@pytest.mark.parametrize(("rate", "expected"), [(0, 95), (1, 105), (0.85, 100), (0.84, 99)])
def test_admissions_feedback_is_bounded_and_has_four_year_lag(inputs, rate, expected):
    inputs[1]["admissions"].update(
        baseline_enrollment=100,
        observed_employment_rate=rate,
        observed_feedback_year=2026,
        minimum_enrollment=90,
        maximum_enrollment=110,
    )
    result = evaluate(inputs)["admissions"]
    assert result["recommended_enrollment"] == expected
    assert result["effective_intake_year"] == result["next_intake_year"] == 2027
    assert result["expected_graduation_year"] == 2031


def test_admissions_missing_feedback_holds_known_scale(inputs):
    inputs[1]["admissions"]["baseline_enrollment"] = 100
    assert evaluate(inputs)["admissions"]["recommended_enrollment"] == 100


def test_synthetic_admissions_stress_is_separate_from_real_decision(inputs):
    inputs[1]["admissions"].update(
        baseline_enrollment=100,
        observed_employment_rate=0,
        observed_feedback_year=2026,
        evidence_mode="synthetic",
    )
    result = evaluate(inputs)["admissions"]
    assert result["recommended_enrollment"] == 100
    assert result["synthetic_recommended_enrollment"] == 95
    assert result["status"] == "synthetic_stress_only"


@pytest.mark.parametrize(
    ("where", "field", "value"),
    [
        ("admissions", "target_rate", 1.1),
        ("admissions", "gain", 10**400),
        ("admissions", "feedback_lag_years", True),
        ("admissions", "baseline_enrollment", 0),
        ("directions", "capacity", -1),
        ("directions", "minimum_score", float("nan")),
        ("risks", "probability_range", [0.8, 0.2]),
        ("risks", "action_id", "missing"),
    ],
)
def test_rejects_invalid_policy_fields_with_actionable_errors(inputs, where, field, value):
    obj = inputs[1][where]
    if isinstance(obj, list):
        obj = obj[0]
    obj[field] = value
    with pytest.raises(ValueError, match=field + ".*请"):
        evaluate(inputs)


def test_rejects_duplicate_risk_ids(inputs):
    inputs[1]["risks"][1]["risk_id"] = "credits"
    with pytest.raises(ValueError, match="risk_id.*请"):
        evaluate(inputs)


def test_rejects_missing_module_and_unknown_course(inputs):
    inputs[1]["student_paths"][0]["module_credits"].pop("sports")
    with pytest.raises(ValueError, match="module_credits.*请"):
        evaluate(inputs)


@pytest.mark.parametrize(
    ("minimum", "maximum", "rate", "expected"),
    [
        (98, 110, 0, 98),
        (90, 102, 1, 102),
        (100, 100, 0, 100),
    ],
)
def test_admissions_absolute_limits_override_proposed_adjustment(
    inputs, minimum, maximum, rate, expected
):
    inputs[1]["admissions"].update(
        baseline_enrollment=100,
        minimum_enrollment=minimum,
        maximum_enrollment=maximum,
        observed_employment_rate=rate,
        observed_feedback_year=2026,
    )
    assert evaluate(inputs)["admissions"]["recommended_enrollment"] == expected


def test_small_enrollment_rounding_never_exceeds_relative_limit(inputs):
    inputs[1]["admissions"].update(
        baseline_enrollment=11, observed_employment_rate=0, observed_feedback_year=2026
    )
    assert evaluate(inputs)["admissions"]["recommended_enrollment"] == 11


def test_strategy_handles_missing_course_hours_without_claiming_validity(inputs):
    inputs[0]["courses"][0]["hours"] = None
    result = evaluate(inputs)
    assert result["scenario_results"][0]["candidates"][1]["status"] == "invalid"
    assert result["scenario_results"][1]["candidates"][1]["status"] == "not_evaluable"
    assert result["termination_reason"] == "revision_options_exhausted"


def test_module_total_overflow_has_actionable_error(inputs):
    inputs[1]["student_paths"][0]["module_credits"].update(professional_core=1e308, sports=1e308)
    with pytest.raises(ValueError, match="module_credits.*溢出.*请"):
        evaluate(inputs)


def test_finite_enrollment_calculation_overflow_is_actionable(inputs):
    inputs[1]["admissions"].update(
        baseline_enrollment=10**308,
        max_relative_change=1.0,
        observed_employment_rate=1,
        observed_feedback_year=2026,
    )
    with pytest.raises(ValueError, match="admissions.*溢出.*请"):
        evaluate(inputs)


def test_feedback_interval_and_training_lag_are_separate(inputs):
    inputs[1]["admissions"].update(
        baseline_enrollment=100,
        observed_employment_rate=1,
        observed_feedback_year=2025,
        feedback_interval_years=2,
    )
    result = evaluate(inputs)["admissions"]
    assert result["next_intake_year"] == 2027
    assert result["expected_graduation_year"] == 2031


def test_direction_scoring_uses_only_courses_before_selection(inputs):
    result = evaluate(inputs)["direction_policy"]
    assert result["score_course_ids"] == ["0610297", "0630121", "0630122", "0630158"]
    assert "0610110" not in result["score_course_ids"]


def test_rejects_incompatible_program_identity(inputs):
    inputs[2]["school"] = "其他学校"
    with pytest.raises(ValueError, match="program.school.*请"):
        evaluate(inputs)


def test_invalid_admissions_evidence_type_is_actionable(inputs):
    inputs[1]["admissions"]["evidence_mode"] = []
    with pytest.raises(ValueError, match="admissions.evidence_mode.*请"):
        evaluate(inputs)


@pytest.mark.parametrize(
    ("cap", "rate", "expected"),
    [(0.15, 1, 115), (0.15, 0, 85), (0.57, 0, 43), (0.1499999, 1, 114), (0.5699999, 0, 44)],
)
def test_decimal_percentage_boundaries_preserve_exact_integer_capacity(inputs, cap, rate, expected):
    inputs[1]["admissions"].update(
        baseline_enrollment=100,
        max_relative_change=cap,
        observed_employment_rate=rate,
        observed_feedback_year=2026,
    )
    assert evaluate(inputs)["admissions"]["recommended_enrollment"] == expected
