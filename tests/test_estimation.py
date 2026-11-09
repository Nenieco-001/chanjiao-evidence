import pytest

from chanjiao_evidence.estimation import analyze_panel


def test_recovers_hand_calculated_did(panel):
    result = analyze_panel(panel, 2022)
    assert result["main"]["estimate"] == pytest.approx(0.06)
    assert result["main"]["treated_change"] == pytest.approx(0.08)
    assert result["main"]["control_change"] == pytest.approx(0.02)
    assert result["main"]["ci95"][0] < 0.06 < result["main"]["ci95"][1]
    assert result["placebo"]["estimate"] == pytest.approx(0, abs=1e-12)
    assert len(result["leave_one_unit_out"]) == 6


def test_null_reform_returns_zero(panel):
    panel.loc[(panel.treated == 1) & (panel.year == 2022), "outcome"] -= 0.06
    assert analyze_panel(panel, 2022)["main"]["estimate"] == pytest.approx(0, abs=1e-12)


def test_harmful_reform_retains_negative_effect(panel):
    panel.loc[(panel.treated == 1) & (panel.year == 2022), "outcome"] -= 0.12
    assert analyze_panel(panel, 2022)["main"]["estimate"] == pytest.approx(-0.06)


def test_pre_reform_divergence_is_visible(panel):
    panel.loc[(panel.treated == 1) & (panel.year == 2020), "outcome"] -= 0.05
    assert analyze_panel(panel, 2022)["placebo"]["estimate"] == pytest.approx(0.05)


def test_row_order_does_not_change_estimates(panel):
    assert analyze_panel(panel, 2022) == analyze_panel(panel.iloc[::-1], 2022)
