import copy

import pytest

from chanjiao_evidence.planning import compare_plans


def test_records_credit_reallocation_and_resource_limits(plans):
    result = compare_plans(plans, {"estimate": 0.06, "ci95": [0.03, 0.09]})
    changes = {row["module"]: row["delta"] for row in result["credit_changes"]}
    assert changes == {"foundation": 0, "internship": 4, "specialty": -4}
    assert sum(changes.values()) == 0
    assert result["baseline_plan_id"] == "unchanged"
    assert result["constraints"]["budget"] == 10


def test_sensitivity_exposes_when_baseline_wins(plans):
    result = compare_plans(plans, {"estimate": 0.06, "ci95": [0.03, 0.09]})
    points = {
        (row["transfer_factor_assumption"], row["bias_budget_assumption"]): row
        for row in result["sensitivity"]
    }
    assert points[(0.5, 0.01)]["conservative_gain"] == pytest.approx(0.005)
    assert points[(0.5, 0.01)]["selected_plan"] == "internship"
    assert points[(0.5, 0.02)]["selected_plan"] == "unchanged"
    assert points[(0, 0)]["selected_plan"] == "unchanged"


def test_infeasible_candidate_never_wins_sensitivity(plans):
    plans["plans"][1]["cost"] = 100
    result = compare_plans(plans, {"estimate": 0.06, "ci95": [0.03, 0.09]})
    assert {point["selected_plan"] for point in result["sensitivity"]} == {"unchanged"}


def test_selects_feasible_reform_with_positive_lower_bound(plans):
    result = compare_plans(plans, {"estimate": 0.06, "ci95": [0.03, 0.09]})
    assert result["selected_plan"] == "internship"
    assert result["plans"][1]["conservative_gain"] == pytest.approx(0.005)


def test_unchanged_plan_wins_when_evidence_is_uncertain(plans):
    result = compare_plans(plans, {"estimate": 0.01, "ci95": [-0.03, 0.05]})
    assert result["selected_plan"] == "unchanged"
    assert result["plans"][1]["conservative_gain"] < 0


def test_transfer_zero_does_not_hide_harm(plans):
    plans["transfer_factors"] = [0, 1]
    result = compare_plans(plans, {"estimate": -0.03, "ci95": [-0.05, -0.01]})
    assert result["plans"][1]["conservative_gain"] == pytest.approx(-0.06)


def test_infeasible_baseline_is_rejected(plans):
    plans["plans"][0]["credits"]["foundation"] = 10
    with pytest.raises(ValueError, match="baseline"):
        compare_plans(plans, {"estimate": 0.06, "ci95": [0.03, 0.09]})


@pytest.mark.parametrize("corruption", ["budget", "credits", "foundation", "capacity"])
def test_resource_violations_are_reported(plans, corruption):
    candidate = plans["plans"][1]
    if corruption == "budget":
        candidate["cost"] = 11
    elif corruption == "credits":
        candidate["credits"]["specialty"] = 9
    elif corruption == "foundation":
        candidate["credits"].update(foundation=10, specialty=14)
    else:
        candidate["credits"].update(internship=7, specialty=9)
    result = compare_plans(plans, {"estimate": 0.06, "ci95": [0.03, 0.09]})
    assert result["selected_plan"] == "unchanged"
    assert result["plans"][1]["feasible"] is False
    assert result["plans"][1]["violations"]


@pytest.mark.parametrize(
    "corruption", ["nan", "duplicate_id", "baseline_missing", "action", "modules"]
)
def test_ambiguous_plan_config_is_rejected(plans, corruption):
    config = copy.deepcopy(plans)
    if corruption == "nan":
        config["transfer_factors"] = [float("nan")]
    elif corruption == "duplicate_id":
        config["plans"][1]["plan_id"] = "unchanged"
    elif corruption == "baseline_missing":
        config["plans"].pop(0)
    elif corruption == "action":
        config["plans"][1]["action_id"] = "different_reform"
    else:
        config["plans"][1]["credits"]["typo"] = config["plans"][1]["credits"].pop("specialty")
    with pytest.raises(ValueError):
        compare_plans(config, {"estimate": 0.06, "ci95": [0.03, 0.09]})
