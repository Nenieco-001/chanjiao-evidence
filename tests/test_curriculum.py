"""Hand-calculated fixtures exercise the published-input shape, not real schools."""

import copy
import json

import pytest

from chanjiao_evidence import curriculum


@pytest.fixture
def curriculum_plan():
    return {
        "schema_version": 1,
        "evidence_mode": "published_curriculum",
        "synthetic_fixture": True,
        "school": "手算测试学校，无真实学校含义",
        "major": "测试专业",
        "program_version": "手算版本",
        "coverage": "selected_courses",
        "source": {
            "title": "手算来源占位，仅用于测试输入格式",
            "url": "https://example.edu/fixture.pdf",
            "sha256": "a" * 64,
            "location": "测试页1",
        },
        "courses": [
            {
                "course_id": "foundation",
                "title": "基础课程（测试）",
                "credits": 4,
                "hours": 64,
                "semester": 2,
                "prerequisites": [],
                "source_location": "测试页1行1",
            },
            {
                "course_id": "donor",
                "title": "调出课程（测试）",
                "credits": 3,
                "hours": 48,
                "semester": 4,
                "prerequisites": ["foundation"],
                "source_location": "测试页1行2",
            },
            {
                "course_id": "target",
                "title": "实践课程（测试）",
                "credits": 2,
                "hours": 32,
                "semester": 4,
                "prerequisites": ["foundation"],
                "source_location": "测试页1行3",
            },
        ],
    }


@pytest.fixture
def curriculum_config():
    return {
        "schema_version": 1,
        "evidence_mode": "scenario_assumptions",
        "label": "手算决策情景",
        "target_course_id": "target",
        "donor_course_id": "donor",
        "hour_options": [8, 16],
        "credit_delta": 0.5,
        "minimum_hours": {"donor": 32},
        "minimum_credits": {"donor": 2},
        "capacity_added_hours": 16,
        "rationale": "假定教师提出把部分课时转入实践课程",
        "assumption_notes": ["课时底线与容量均为测试假设"],
    }


def test_interface_exists_before_implementation():
    assert callable(getattr(curriculum, "evaluate_curriculum", None))


def test_preserves_published_facts_and_separates_scenario(curriculum_plan, curriculum_config):
    result = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    assert result["evidence_mode"] == "published_curriculum"
    assert result["coverage"] == "selected_courses"
    assert result["curriculum"] == curriculum_plan
    assert result["scenario_assumptions"] == curriculum_config
    assert result["curriculum"]["courses"][1]["hours"] == 48
    assert result["candidates"][1]["course_changes"][0]["source_location"]
    assert result["employment_effect"]["status"] == "unidentified"
    assert result["employment_effect"]["missing_evidence"]
    assert result["assumptions"] == curriculum_config["assumption_notes"]
    assert result["limitations"]


def test_baseline_keeps_every_value_and_is_default(curriculum_plan, curriculum_config):
    result = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    baseline = result["candidates"][0]
    assert baseline["candidate_id"] == result["baseline_candidate_id"] == "unchanged"
    assert baseline["added_hours"] == baseline["credit_delta"] == 0
    assert baseline["feasible"] is True
    for change in baseline["course_changes"]:
        assert change["hours_before"] == change["hours_after"]
        assert change["credits_before"] == change["credits_after"]
    assert result["selected_candidate_id"] == "unchanged"
    assert result["review_candidate_ids"] == ["transfer_1", "transfer_2"]


def test_transfers_hours_and_credits_without_changing_total(curriculum_plan, curriculum_config):
    result = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    candidate = result["candidates"][2]
    changes = {row["course_id"]: row for row in candidate["course_changes"]}
    assert changes["target"]["hours_after"] == 48
    assert changes["target"]["credits_after"] == 2.5
    assert changes["donor"]["hours_after"] == 32
    assert changes["donor"]["credits_after"] == 2.5
    assert changes["target"]["title"] == "实践课程（测试）"
    assert changes["target"]["reason"] == curriculum_config["rationale"]
    assert candidate["totals"] == {
        "hours_before": 144,
        "hours_after": 144,
        "credits_before": 9,
        "credits_after": 9,
    }
    assert candidate["practice_input_proxy"]["added_hours"] == 16
    assert candidate["practice_input_proxy"]["student_mastery_effect"] == "unidentified"


@pytest.mark.parametrize("field", ["hours", "credits"])
def test_unknown_amounts_remain_null_and_make_candidates_not_evaluable(
    curriculum_plan, curriculum_config, field
):
    curriculum_plan["courses"][1][field] = None
    curriculum_plan["courses"][1]["duration_text"] = "2周，未公开折算课时"
    result = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    for candidate in result["candidates"]:
        assert candidate["status"] == "not_evaluable"
        assert candidate["evaluable"] is False
        assert candidate["feasible"] is None
        assert f"courses.donor.{field}" in candidate["missing_inputs"]
        donor = next(row for row in candidate["course_changes"] if row["course_id"] == "donor")
        assert donor[f"{field}_after"] is None
        assert candidate["totals"][f"{field}_after"] is None
    assert result["selected_candidate_id"] == "unchanged"
    assert result["review_candidate_ids"] == []


@pytest.mark.parametrize(
    ("updates", "violation"),
    [
        ({"minimum_hours": {"donor": 40}}, "minimum_hours:donor"),
        ({"minimum_credits": {"donor": 3}}, "minimum_credits:donor"),
        ({"hour_options": [56]}, "nonnegative_hours:donor"),
        ({"credit_delta": 4}, "nonnegative_credits:donor"),
        ({"capacity_added_hours": 0}, "capacity_added_hours"),
    ],
)
def test_keeps_infeasible_candidates_and_explains_failed_constraint(
    curriculum_plan, curriculum_config, updates, violation
):
    curriculum_config.update(updates)
    result = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    candidate = result["candidates"][-1]
    assert candidate["status"] == "infeasible"
    assert candidate["feasible"] is False
    assert violation in candidate["violations"]
    assert result["selected_candidate_id"] == "unchanged"


@pytest.mark.parametrize("semester", [4, 5])
def test_reports_known_prerequisite_semester_conflict(curriculum_plan, curriculum_config, semester):
    curriculum_plan["courses"][0]["semester"] = semester
    result = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    for candidate in result["candidates"]:
        assert "prerequisite_order:foundation->target" in candidate["violations"]
        assert "prerequisite_order:foundation->donor" in candidate["violations"]
        assert candidate["feasible"] is False


def test_missing_prerequisites_and_semesters_are_explicit_gaps(curriculum_plan, curriculum_config):
    curriculum_plan["courses"][1]["prerequisites"] = ["outside_selected_courses"]
    curriculum_plan["courses"][2]["semester"] = None
    curriculum_plan["courses"][2]["prerequisites_status"] = "not_published"
    result = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    assert (
        "prerequisite_not_modeled:outside_selected_courses->donor"
        in result["unverified_constraints"]
    )
    assert "semester_not_published:target" in result["unverified_constraints"]
    assert "prerequisites_not_published:target" in result["unverified_constraints"]
    assert result["candidates"][1]["feasible"] is True
    assert result["employment_effect"]["status"] == "unidentified"


def test_process_log_revises_a_failed_candidate_to_smaller_feasible_transfer(
    curriculum_plan, curriculum_config
):
    curriculum_config["capacity_added_hours"] = 8
    result = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    events = [row for row in result["process_log"] if row["candidate_id"] == "transfer_2"]
    assert [row["stage"] for row in events] == [
        "generation",
        "evaluation",
        "reflection",
        "revision",
    ]
    assert events[1]["violations"] == ["capacity_added_hours"]
    assert events[2]["constraint_gaps"]
    assert events[3]["revised_candidate_id"] == "transfer_1"
    assert result["selected_candidate_id"] == "unchanged"


def test_zero_option_keeps_only_baseline_without_implied_benefit(
    curriculum_plan, curriculum_config
):
    curriculum_config.update(hour_options=[0], credit_delta=0)
    result = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["practice_input_proxy"]["added_hours"] == 0
    assert result["selected_candidate_id"] == "unchanged"
    assert "estimated_gain" not in json.dumps(result)


def test_zero_and_duplicate_options_do_not_create_extra_credit_transfers(
    curriculum_plan, curriculum_config
):
    curriculum_config["hour_options"] = [0, 16, 16]
    result = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    assert [row["candidate_id"] for row in result["candidates"]] == ["unchanged", "transfer_1"]
    baseline, transfer = result["candidates"]
    assert baseline["added_hours"] == baseline["credit_delta"] == 0
    assert [row["credits_after"] for row in baseline["course_changes"]] == [3, 2]
    assert transfer["added_hours"] == 16
    assert transfer["credit_delta"] == 0.5
    assert result["review_candidate_ids"] == ["transfer_1"]


def test_inputs_and_returned_facts_do_not_alias_and_output_is_deterministic(
    curriculum_plan, curriculum_config
):
    original_plan, original_config = copy.deepcopy((curriculum_plan, curriculum_config))
    first = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    second = curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(
        second, ensure_ascii=False, sort_keys=True
    )
    assert (curriculum_plan, curriculum_config) == (original_plan, original_config)
    first["curriculum"]["source"]["title"] = "修改输出"
    first["scenario_assumptions"]["minimum_hours"]["donor"] = 0
    assert (curriculum_plan, curriculum_config) == (original_plan, original_config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evidence_mode", "synthetic"),
        ("schema_version", True),
        ("coverage", "whole_program"),
        ("source", {"title": "missing provenance"}),
        ("courses", []),
    ],
)
def test_rejects_invalid_curriculum_boundary(curriculum_plan, curriculum_config, field, value):
    curriculum_plan[field] = value
    with pytest.raises(ValueError, match=field):
        curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evidence_mode", "published_curriculum"),
        ("target_course_id", "missing"),
        ("donor_course_id", "target"),
        ("hour_options", [-8]),
        ("hour_options", [float("nan")]),
        ("hour_options", [True]),
        ("credit_delta", -0.5),
        ("minimum_hours", {"donor": -1}),
        ("minimum_credits", {"missing": 1}),
        ("capacity_added_hours", float("inf")),
        ("assumption_notes", "no list"),
    ],
)
def test_rejects_invalid_scenario_changes_at_boundary(
    curriculum_plan, curriculum_config, field, value
):
    curriculum_config[field] = value
    with pytest.raises(ValueError, match=field):
        curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)


@pytest.mark.parametrize("field", ["hours", "credits", "semester"])
def test_rejects_negative_published_amounts(curriculum_plan, curriculum_config, field):
    curriculum_plan["courses"][1][field] = -1
    with pytest.raises(ValueError, match=field):
        curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)


def test_rejects_duplicate_course_ids(curriculum_plan, curriculum_config):
    curriculum_plan["courses"][1]["course_id"] = "target"
    with pytest.raises(ValueError, match="course_id"):
        curriculum.evaluate_curriculum(curriculum_plan, curriculum_config)
