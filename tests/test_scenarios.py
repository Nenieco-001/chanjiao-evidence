import copy
import json
import math
from pathlib import Path

import pytest


@pytest.fixture
def evidence():
    return json.loads(Path("data/evidence/internships.json").read_text(encoding="utf-8"))


@pytest.fixture
def config():
    return json.loads(Path("data/examples/effect-scenarios.json").read_text(encoding="utf-8"))


def evaluate(evidence, config):
    from chanjiao_evidence.scenarios import evaluate_scenarios

    return evaluate_scenarios(evidence, config)


def test_reference_scenarios_preserve_log_units_and_unidentified_target(evidence, config):
    result = evaluate(evidence, config)
    assert result["status"] == "literature_reference_scenarios"
    assert result["target_effect"]["status"] == "unidentified"
    assert result["target_effect"]["observed_causal_effect"] is False
    assert result["reference"]["unit"] == "log_points"
    assert result["reference"]["value"] == 0.065
    assert result["reference"]["standard_error"] == 0.019
    assert result["reference"]["ci95"] == pytest.approx([0.02776, 0.10224])
    assert result["reference"]["source_version"] == evidence["cards"][0]["source_version"]
    assert (
        result["reference"]["source_location"]
        == evidence["cards"][0]["reported_results"][0]["source_location"]
    )
    assert result["missing_evidence"]
    pessimistic, base, optimistic = result["scenarios"]
    assert pessimistic["estimate"] == -0.01
    assert pessimistic["interval"] == [-0.01, -0.01]
    assert base["estimate"] == pytest.approx(0.0225)
    assert base["interval"] == pytest.approx([0.00388, 0.04112])
    assert optimistic["estimate"] == 0.065
    assert optimistic["relative_income_percent"]["estimate"] == pytest.approx(6.715902438)
    assert optimistic["bias_thresholds"] == pytest.approx(
        {"point_estimate": 0.065, "interval_lower": 0.02776}
    )
    assert result["zero_effect_comparison"] == {"estimate": 0.0, "unit": "log_points"}


@pytest.mark.parametrize("status", ["supported", "mismatch"])
def test_applicability_never_becomes_observed_causal_effect(evidence, config, status):
    config["applicability"]["status"] = status
    result = evaluate(evidence, config)
    expected = "conditional_projection" if status == "supported" else "unidentified"
    assert result["target_effect"]["status"] == expected
    assert result["target_effect"]["observed_causal_effect"] is False
    assert result["status"] == (
        "conditional_projection" if status == "supported" else "literature_reference_scenarios"
    )


def test_proportion_difference_without_se_has_no_sampling_interval(evidence, config):
    config["effect_reference"] = {
        "evidence_id": "baert_2021_internships",
        "outcome_id": "invitation to a job interview",
    }
    result = evaluate(evidence, config)
    assert result["reference"]["value"] == 0.025
    assert result["reference"]["unit"] == "proportion_difference"
    assert result["reference"]["standard_error"] is None
    assert result["reference"]["ci95"] is None
    assert result["identification_status"] == "reported_value_only_no_sampling_ci"
    assert result["scenarios"][1]["estimate"] == pytest.approx(0.0025)
    assert result["scenarios"][1]["interval"] == pytest.approx([0.0025, 0.0025])
    assert result["scenarios"][1]["interval_kind"] == "reported_value_only"
    assert "relative_income_percent" not in result["scenarios"][1]


@pytest.mark.parametrize("value", [0, -0.02])
def test_zero_and_negative_references_and_thresholds_are_retained(evidence, config, value):
    evidence["cards"][0]["reported_results"][0]["value"] = value
    result = evaluate(evidence, config)
    assert result["reference"]["value"] == value
    assert result["scenarios"][2]["estimate"] == value
    assert result["scenarios"][2]["bias_thresholds"]["point_estimate"] == value
    assert result["scenarios"][2]["positive_point_advantage"] is False


def test_no_forced_monotonicity_or_input_mutation(evidence, config):
    config["scenarios"][0]["transfer_factor"] = 1
    config["scenarios"][0]["bias"] = 0
    config["scenarios"][2]["transfer_factor"] = 0
    before = copy.deepcopy((evidence, config))
    result = evaluate(evidence, config)
    assert result["scenarios"][0]["estimate"] == 0.065
    assert result["scenarios"][2]["estimate"] == 0
    assert (evidence, config) == before


@pytest.mark.parametrize("invalid", [None, [], "bad", True, 0])
def test_source_documents_must_be_objects(evidence, config, invalid):
    with pytest.raises(ValueError, match="evidence"):
        evaluate(invalid, config)
    with pytest.raises(ValueError, match="config"):
        evaluate(evidence, invalid)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("evidence_mode", "historical"),
        ("action_id", " "),
        ("target_population", None),
        ("target_action", []),
        ("applicability", None),
        ("effect_reference", []),
        ("scenarios", []),
    ],
)
def test_invalid_config_reports_field_and_repair(evidence, config, field, value):
    config[field] = value
    with pytest.raises(ValueError, match=field) as error:
        evaluate(evidence, config)
    assert "请" in str(error.value)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), 10**1000, -0.01, 1.01])
def test_transfer_factor_rejects_nonfinite_and_out_of_range(evidence, config, value):
    config["scenarios"][0]["transfer_factor"] = value
    with pytest.raises(ValueError, match="transfer_factor"):
        evaluate(evidence, config)


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), 10**1000, -0.01])
def test_bias_rejects_invalid_numbers(evidence, config, value):
    config["scenarios"][0]["bias"] = value
    with pytest.raises(ValueError, match="bias"):
        evaluate(evidence, config)


@pytest.mark.parametrize("field", ["value", "standard_error"])
@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), 10**1000, "0.02"])
def test_reference_numbers_are_validated(evidence, config, field, value):
    evidence["cards"][0]["reported_results"][0][field] = value
    with pytest.raises(ValueError, match=field):
        evaluate(evidence, config)


def test_negative_standard_error_is_rejected(evidence, config):
    evidence["cards"][0]["reported_results"][0]["standard_error"] = -0.019
    with pytest.raises(ValueError, match="standard_error"):
        evaluate(evidence, config)


@pytest.mark.parametrize("mode", ["missing", "duplicate", "unsupported_unit", "qualitative"])
def test_result_selection_rejects_ambiguous_or_unusable_metrics(evidence, config, mode):
    rows = evidence["cards"][0]["reported_results"]
    if mode == "missing":
        config["effect_reference"]["outcome_id"] = "unknown"
    elif mode == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif mode == "unsupported_unit":
        rows[0]["unit"] = "percentage_points"
    else:
        config["effect_reference"]["outcome_id"] = "early-career unemployment"
    with pytest.raises(ValueError, match="outcome_id|unit|value"):
        evaluate(evidence, config)


@pytest.mark.parametrize("mode", ["missing", "duplicate", "nonobject"])
def test_three_named_scenarios_are_required(evidence, config, mode):
    if mode == "missing":
        config["scenarios"].pop()
    elif mode == "duplicate":
        config["scenarios"][2]["scenario_id"] = "base"
    else:
        config["scenarios"][0] = []
    with pytest.raises(ValueError, match="scenarios"):
        evaluate(evidence, config)


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "verified"),
        ("rationale", ""),
        ("source_locations", []),
        ("source_locations", [1]),
    ],
)
def test_applicability_requires_traceable_assessment(evidence, config, field, value):
    config["applicability"][field] = value
    with pytest.raises(ValueError, match=field):
        evaluate(evidence, config)


def test_assumption_source_is_required(evidence, config):
    config["scenarios"][0]["assumption_source"] = ""
    with pytest.raises(ValueError, match="assumption_source"):
        evaluate(evidence, config)


def test_overflow_in_derived_interval_is_rejected(evidence, config):
    evidence["cards"][0]["reported_results"][0]["standard_error"] = 1e308
    with pytest.raises(ValueError, match="standard_error|ci95"):
        evaluate(evidence, config)


def test_unrepresentable_income_conversion_is_explicit(evidence, config):
    evidence["cards"][0]["reported_results"][0]["value"] = 1000
    result = evaluate(evidence, config)
    conversion = result["scenarios"][2]["relative_income_percent"]
    assert conversion["status"] == "outside_numeric_range"
    assert conversion["estimate"] is None
    assert result["scenarios"][2]["estimate"] == 1000
    assert math.isfinite(result["scenarios"][2]["estimate"])


def test_all_metrics_in_selected_card_require_unique_ids(evidence, config):
    rows = evidence["cards"][0]["reported_results"]
    rows.append(copy.deepcopy(rows[1]))
    with pytest.raises(ValueError, match="outcome_id"):
        evaluate(evidence, config)


def test_result_source_uses_https_original_link(evidence, config):
    evidence["cards"][0]["reported_results"][0]["source_url"] = "javascript:alert(1)"
    with pytest.raises(ValueError, match="source_url"):
        evaluate(evidence, config)


@pytest.mark.parametrize("value", [None, {}, [], ""])
def test_reported_source_version_is_required(evidence, config, value):
    evidence["cards"][0]["source_version"] = value
    with pytest.raises(ValueError, match="source_version"):
        evaluate(evidence, config)


def test_large_finite_assumptions_cannot_overflow_projection(evidence, config):
    evidence["cards"][0]["reported_results"][0]["value"] = -1e308
    config["scenarios"][2]["bias"] = 1e308
    with pytest.raises(ValueError, match="estimate|interval"):
        evaluate(evidence, config)


def test_zero_standard_error_is_retained(evidence, config):
    evidence["cards"][0]["reported_results"][0]["standard_error"] = 0
    result = evaluate(evidence, config)
    assert result["reference"]["ci95"] == [0.065, 0.065]
    assert result["scenarios"][2]["interval"] == [0.065, 0.065]


def test_nonincome_log_metric_retains_its_original_meaning(evidence, config):
    card = evidence["cards"][0]
    card["outcomes"] = ["log_skill_score"]
    card["reported_results"][0].update(
        outcome_id="log_skill_score",
        label="技能测试分数对数差",
        interpretation="技能测试对数分数差，未观察收入",
    )
    config["effect_reference"]["outcome_id"] = "log_skill_score"
    result = evaluate(evidence, config)
    assert result["reference"]["outcome_id"] == "log_skill_score"
    assert result["reference"]["label"] == "技能测试分数对数差"
    assert result["reference"]["unit"] == "log_points"
    assert result["scenarios"][2]["estimate"] == 0.065
    assert all("relative_income_percent" not in row for row in result["scenarios"])


@pytest.mark.parametrize(
    "bias,positive",
    [
        (0.032499999998, True),
        (0.03249999999999999, False),
        (0.0325, False),
        (0.032500000002, False),
    ],
)
def test_point_advantage_uses_zero_tolerance(evidence, config, bias, positive):
    config["scenarios"][1]["bias"] = bias
    base = evaluate(evidence, config)["scenarios"][1]
    assert base["positive_point_advantage"] is positive
    assert base["bias_thresholds"]["point_estimate"] == 0.0325
    if bias == 0.03249999999999999:
        assert 0 < base["estimate"] < 1e-12


@pytest.mark.parametrize(
    "bias,positive",
    [(0.013879999998, True), (0.01388, False), (0.013880000002, False)],
)
def test_lower_advantage_uses_zero_tolerance(evidence, config, bias, positive):
    config["scenarios"][1]["bias"] = bias
    base = evaluate(evidence, config)["scenarios"][1]
    assert base["positive_lower_advantage"] is positive
    assert base["bias_thresholds"]["interval_lower"] == pytest.approx(0.01388)
    if bias == 0.01388:
        assert 0 < base["interval"][0] < 1e-12


def test_bias_cannot_project_a_proportion_difference_outside_its_parameter_range(evidence, config):
    config["effect_reference"] = {
        "evidence_id": "baert_2021_internships",
        "outcome_id": "invitation to a job interview",
    }
    config["scenarios"][0]["bias"] = 2
    with pytest.raises(ValueError, match=r"scenarios\[0\].bias") as error:
        evaluate(evidence, config)
    assert "[-1,1]" in str(error.value)
    assert "请" in str(error.value)


def test_normal_reference_interval_may_cross_proportion_parameter_bounds(evidence, config):
    config["effect_reference"] = {
        "evidence_id": "baert_2021_internships",
        "outcome_id": "invitation to a job interview",
    }
    evidence["cards"][1]["reported_results"][0].update(value=0.95, standard_error=0.1)
    result = evaluate(evidence, config)
    optimistic = result["scenarios"][2]
    assert optimistic["estimate"] == 0.95
    assert optimistic["interval"] == pytest.approx([0.754, 1.146])
    assert optimistic["interval_kind"] == "transferred_reference_normal_95"
