import copy
import json
from pathlib import Path

import pytest

from chanjiao_evidence.evidence import parse_evidence
from chanjiao_evidence.scenarios import evaluate_scenarios


def inputs():
    evidence = json.loads(Path("data/evidence/course-projects.json").read_text(encoding="utf-8"))
    config = json.loads(
        Path("data/examples/project-effect-scenarios.json").read_text(encoding="utf-8")
    )
    return evidence, config


@pytest.mark.parametrize(
    "filename,expected_text",
    [
        ("data/evidence/course-projects.json", "课程项目"),
        ("data/examples/project-effect-scenarios.json", "中财"),
    ],
)
def test_project_inputs_preserve_utf8_text(filename, expected_text):
    content = Path(filename).read_bytes()
    text = content.decode("utf-8")
    assert expected_text in text
    assert content.count(b"?") == 0
    assert any(value >= 128 for value in content)
    assert json.loads(text)


def test_project_cards_separate_design_null_results_and_effect_reference():
    evidence, _ = inputs()
    parsed = parse_evidence(json.dumps(evidence).encode(), "learning_outcomes_smd")
    assert len(parsed["cards"]) == 4
    assert evidence["target_action_review"]["hour_dose_effect_status"] == "unidentified"
    trial = next(c for c in parsed["cards"] if c["evidence_id"] == "wlodarski_2021_process")
    assert trial["treatment_assignment"] == "alphabetical_laboratory_groups"
    assert trial["quantitative_effect_usable"] is False
    assert trial["null_or_adverse_results"]
    meta = next(c for c in parsed["cards"] if c["evidence_id"] == "zhang_ma_2023_project_learning")
    assert meta["reported_results"][0]["effect_count"] == 57
    assert meta["quality_flags"]


def test_reported_learning_interval_preserves_sd_units_and_zero_base():
    result = evaluate_scenarios(*inputs())
    assert result["reference"]["unit"] == "standardized_mean_difference"
    assert result["reference"]["value"] == 0.116
    assert result["reference"]["standard_error"] is None
    assert result["reference"]["ci95"] == [0.027, 0.204]
    assert result["identification_status"] == "reported_ci95_reference_only"
    pessimistic, base, optimistic = result["scenarios"]
    assert pessimistic["estimate"] == -0.03
    assert base["estimate"] == 0
    assert optimistic["estimate"] == pytest.approx(0.058)
    assert optimistic["interval"] == pytest.approx([0.0135, 0.102])
    assert optimistic["interval_kind"] == "transferred_reported_ci95"
    assert all("relative_income_percent" not in r for r in result["scenarios"])
    assert result["target_effect"]["status"] == "unidentified"
    assert result["target_effect"]["observed_causal_effect"] is False
    assert not any("缺标准误" in gap for gap in result["missing_evidence"])


@pytest.mark.parametrize(
    "interval",
    [
        [],
        [0.1],
        [0, 0.1, 0.2],
        [True, 0.2],
        [0.3, 0.1],
        [0, float("nan")],
        [0, 10**400],
        "0.027,0.204",
        {"lower": 0.027},
    ],
)
def test_malformed_reported_intervals_are_field_errors(interval):
    evidence, config = inputs()
    evidence["cards"][2]["reported_results"][0]["reported_ci95"] = interval
    with pytest.raises(ValueError, match="reported_ci95"):
        evaluate_scenarios(evidence, config)


def test_reported_interval_takes_priority_over_normal_approximation():
    evidence, config = inputs()
    evidence["cards"][2]["reported_results"][0]["standard_error"] = 1e308
    result = evaluate_scenarios(evidence, config)
    assert result["reference"]["ci95"] == [0.027, 0.204]


def test_learning_reference_is_repeatable_and_leaves_inputs_unchanged():
    evidence, config = inputs()
    before = copy.deepcopy((evidence, config))
    assert evaluate_scenarios(evidence, config) == evaluate_scenarios(evidence, config)
    assert (evidence, config) == before
