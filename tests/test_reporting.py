from copy import deepcopy
from html.parser import HTMLParser
from importlib import import_module

import pytest


@pytest.fixture
def report():
    return {
        "schema_version": 1,
        "metadata": {
            "evidence_mode": "synthetic",
            "outcome_id": "employment_rate",
            "outcome_window": "毕业半年内",
            "population": "16个合成专业",
            "action_id": "supervised_internship",
            "adoption_year": 2022,
            "data_license": "MIT，合成数据",
            "sources": [{"title": "合成生成器", "url": "synthetic://generator/v1"}],
        },
        "trajectory": [
            {"year": 2020, "treated_mean": 0.60, "control_mean": 0.50},
            {"year": 2021, "treated_mean": 0.62, "control_mean": 0.52},
            {"year": 2022, "treated_mean": 0.68, "control_mean": 0.54},
        ],
        "analysis": {
            "main": {
                "before_year": 2021,
                "after_year": 2022,
                "estimate": 0.04,
                "standard_error": 0.01,
                "ci95": [0.02, 0.06],
                "treated_change": 0.06,
                "control_change": 0.02,
                "treated_units": 8,
                "control_units": 8,
                "method": "equal-unit change-score OLS, HC3 covariance, t interval",
            },
            "placebo": {
                "before_year": 2020,
                "after_year": 2021,
                "estimate": 0.0,
                "ci95": [-0.01, 0.01],
            },
            "leave_one_unit_out": [
                {"excluded_unit": "T1", "estimate": 0.035},
                {"excluded_unit": "C1", "estimate": 0.045},
            ],
            "bias_to_erase_point_estimate": 0.04,
            "assumptions": ["平行趋势", "无提前反应或干扰", "指标口径稳定"],
        },
        "planning": {
            "selected_plan": "internship",
            "baseline_plan_id": "unchanged",
            "bias_budget_assumption": 0.005,
            "constraints": {
                "total_credits": 30,
                "minimum_credits": {"foundation": 12},
                "maximum_credits": {"internship": 6},
                "budget": 10,
            },
            "credit_changes": [
                {"module": "foundation", "baseline": 14, "candidate": 14, "delta": 0},
                {"module": "specialty", "baseline": 14, "candidate": 10, "delta": -4},
                {"module": "internship", "baseline": 2, "candidate": 6, "delta": 4},
            ],
            "plans": [
                {
                    "plan_id": "unchanged",
                    "cost": 0,
                    "credits": {"foundation": 14, "specialty": 14, "internship": 2},
                    "feasible": True,
                    "violations": [],
                    "conservative_gain": 0.0,
                    "scenarios": [],
                },
                {
                    "plan_id": "internship",
                    "cost": 8,
                    "credits": {"foundation": 14, "specialty": 10, "internship": 6},
                    "feasible": True,
                    "violations": [],
                    "conservative_gain": 0.005,
                    "scenarios": [
                        {
                            "transfer_factor_assumption": 0.5,
                            "estimated_gain": 0.02,
                            "lower_gain_with_bias_budget": 0.005,
                        }
                    ],
                },
            ],
            "sensitivity": [
                {
                    "transfer_factor_assumption": 0.5,
                    "bias_budget_assumption": 0.005,
                    "conservative_gain": 0.005,
                    "selected_plan": "internship",
                },
                {
                    "transfer_factor_assumption": 0.5,
                    "bias_budget_assumption": 0.02,
                    "conservative_gain": -0.01,
                    "selected_plan": "unchanged",
                },
            ],
        },
        "evidence": {
            "status": "literature_context",
            "used_for_estimation": False,
            "cards": [
                {
                    "evidence_id": "baert_2021_internships",
                    "title": "Student internships and employment opportunities after graduation",
                    "authors": ["Stijn Baert", "Brecht Neyt"],
                    "year": 2021,
                    "source_url": "https://example.org/paper?version=1&lang=en",
                    "design": "randomized correspondence field experiment",
                    "outcomes": ["invitation to a job interview"],
                    "population": "fictional graduate applications",
                    "action": "internship experience on resumes",
                    "transfer_limits": ["回邀不等于最终就业"],
                    "data_status": "replication data not acquired",
                    "matches_target_outcome": False,
                    "summary": "随机改变简历实习经历，观察招聘回邀。",
                    "data_access": {"instruction": "向作者申请复现材料"},
                }
            ],
        },
        "limitations": ["缺少真实学校的改革执行记录和同口径就业结果。"],
    }


def render(report, format_name):
    return getattr(import_module("chanjiao_evidence.reporting"), f"render_{format_name}")(report)


@pytest.mark.parametrize("format_name", ["html", "markdown"])
def test_report_preserves_effect_units_and_complete_comparison(report, format_name):
    output = render(report, format_name)
    for value in [
        "合成",
        "employment_rate",
        "毕业半年内",
        "4.00",
        "2.00",
        "6.00",
        "百分点",
        "62.00%",
        "68.00%",
        "52.00%",
        "54.00%",
        "2020",
        "2021",
        "2022",
        "伪改革",
        "逐单位删除",
        "T1",
        "C1",
        "3.50",
        "4.50",
        "unchanged",
        "internship",
        "foundation",
        "specialty",
        "14",
        "10",
        "预算",
        "可行",
        "敏感性",
        "0.50",
        "0.50",
        "-1.00",
        "平行趋势",
        "真实学校",
    ]:
        assert value in output


@pytest.mark.parametrize("format_name", ["html", "markdown"])
@pytest.mark.parametrize("effect, label", [(0.04, "正效应"), (0.0, "零效应"), (-0.04, "负效应")])
def test_report_keeps_positive_zero_and_negative_results(report, format_name, effect, label):
    report["analysis"]["main"]["estimate"] = effect
    report["analysis"]["main"]["ci95"] = [effect - 0.02, effect + 0.02]
    report["planning"]["selected_plan"] = "unchanged" if effect <= 0 else "internship"
    output = render(report, format_name)
    assert label in output
    assert f"{effect * 100:.2f}" in output
    if effect <= 0:
        assert "保持原方案" in output


@pytest.mark.parametrize("format_name", ["html", "markdown"])
def test_historical_report_describes_conditional_estimate(report, format_name):
    report["metadata"]["evidence_mode"] = "historical"
    output = render(report, format_name)
    assert "历史" in output
    assert "识别假设" in output
    assert "这批" in output


@pytest.mark.parametrize("format_name", ["html", "markdown"])
def test_missing_literature_names_materials_needed(report, format_name):
    report["evidence"] = {"status": "not_provided", "used_for_estimation": False, "cards": []}
    output = render(report, format_name)
    assert "未提供论文证据" in output
    assert "原文" in output
    assert "数据" in output
    assert "used_for_estimation=false" in output


@pytest.mark.parametrize("format_name", ["html", "markdown"])
def test_literature_reports_target_mismatch_and_access_status(report, format_name):
    output = render(report, format_name)
    for value in [
        "目标指标不匹配",
        "invitation to a job interview",
        "回邀不等于最终就业",
        "randomized correspondence field experiment",
        "replication data not acquired",
        "向作者申请复现材料",
        "used_for_estimation=false",
        "example.org/paper",
    ]:
        assert value in output


@pytest.mark.parametrize("format_name", ["html", "markdown"])
def test_structured_paper_details_have_readable_labels(report, format_name):
    report["evidence"]["cards"][0].update(
        {
            "reported_results": [
                {
                    "outcome_id": "interview_invitation",
                    "label": "面试回邀",
                    "value": 0.126,
                    "unit": "relative_change",
                    "interpretation": "相对增加12.6%",
                    "source_location": "Table 3",
                    "source_url": "https://example.org/paper",
                }
            ],
            "source_locations": [
                {
                    "label": "结果表",
                    "url": "https://example.org/paper",
                    "location": "Table 3",
                    "version": "作者稿",
                }
            ],
            "data_access": {
                "status": "not_acquired",
                "materials_obtained": ["论文PDF"],
                "microdata_acquired": False,
                "public_download_verified": False,
                "access_routes": [{"label": "申请页", "url": "https://example.org/data"}],
                "next_step": "向作者申请微观数据",
            },
        }
    )
    output = render(report, format_name)
    for value in ["报告值", "相对增加12.6%", "原文定位", "Table 3", "已取得微观数据", "否"]:
        assert value in output
    assert "{'status':" not in output


@pytest.mark.parametrize("format_name", ["html", "markdown"])
def test_qualitative_paper_result_keeps_explanation_without_inventing_zero(report, format_name):
    report["evidence"]["cards"][0]["reported_results"] = [
        {
            "outcome_id": "unemployment",
            "label": "早期失业",
            "interpretation": "原文报告早期失业减少，本卡片保留定性解释。",
            "source_location": "结果章节",
        }
    ]
    output = render(report, format_name)
    assert "未从原文提取数值" in output
    assert "原文报告早期失业减少，本卡片保留定性解释。" in output


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def test_html_escapes_external_text_and_blocks_unsafe_links(report):
    payload = '<script>alert(1)</script><img src=x onerror="alert(1)">'
    report["metadata"]["population"] = payload
    report["metadata"]["sources"] = [
        {"title": payload, "url": "javascript:alert(1)"},
        {"title": "伪协议", "url": "https://example.org/\nonclick=evil"},
    ]
    report["evidence"]["cards"][0]["title"] = payload
    report["evidence"]["cards"][0]["source_url"] = "data:text/html,<script>alert(1)</script>"
    output = render(report, "html")
    parser = Elements()
    parser.feed(output)
    assert "&lt;script&gt;" in output
    assert all(tag not in {"script", "img", "iframe"} for tag, _ in parser.elements)
    assert all(not key.startswith("on") for _, attrs in parser.elements for key in attrs)
    assert all(
        attrs.get("href", "").startswith(("http://", "https://"))
        for tag, attrs in parser.elements
        if tag == "a"
    )


def test_markdown_escapes_raw_html_and_link_syntax(report):
    report["metadata"]["population"] = "<script>x</script> [打开](javascript:alert(1))"
    report["evidence"]["cards"][0]["source_url"] = "javascript:alert(1)"
    report["evidence"]["cards"][0]["summary"] = "[恶意](data:text/html,boom) | 换列"
    output = render(report, "markdown")
    assert "<script>" not in output
    assert "[打开](javascript:" not in output
    assert "[恶意](data:" not in output
    assert "](javascript:" not in output
    assert r"\| 换列" in output


@pytest.mark.parametrize("format_name", ["html", "markdown"])
def test_report_rendering_is_deterministic_and_does_not_mutate_input(report, format_name):
    original = deepcopy(report)
    assert render(report, format_name) == render(report, format_name)
    assert report == original


def test_html_is_self_contained_and_printable(report):
    output = render(report, "html")
    assert '<html lang="zh-CN">' in output
    assert "@media print" in output
    assert "<table>" in output
    assert "<script" not in output
    assert "<link " not in output
    assert "<svg" not in output


def test_html_title_follows_input_action(report):
    report["metadata"]["action_id"] = "curriculum_reform"
    assert "培养改革，值得调整培养方案吗？" in render(report, "html")
    report["metadata"]["action_id"] = "supervised_internship"
    assert "有指导的企业实习，值得调整培养方案吗？" in render(report, "html")
