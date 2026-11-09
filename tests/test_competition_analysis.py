"""需求侧规则的合成反例，不含真实学校或招聘记录。"""

import csv
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "analysis/competition/workbench.py"


@pytest.fixture
def wb():
    spec = importlib.util.spec_from_file_location("competition_workbench", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_input(tmp_path, year=2026):
    path = tmp_path / f"jobs{year}.csv"
    fields = [
        "企业名称",
        "招聘岗位",
        "工作城市",
        "上市公司行业",
        "招聘发布年份",
        "招聘发布日期",
        "最低月薪",
        "最高月薪",
        "职位描述",
        "学历要求",
        "要求经验",
        "招聘类别",
        "初级分类",
        "来源",
        "",
    ]
    row = dict.fromkeys(fields, "")
    row.update(
        {
            "企业名称": "合成企业",
            "招聘岗位": "软件工程师",
            "工作城市": "北京市",
            "上市公司行业": "软件和信息技术服务业",
            "招聘发布年份": f"{year}.0",
            "招聘发布日期": f"{year}-01-02",
            "最低月薪": "10000",
            "最高月薪": "20000",
            "职位描述": "熟悉Python\n掌握SQL",
            "学历要求": "本科",
            "来源": "合成平台",
        }
    )
    rows = [row, row.copy(), dict(row, 企业名称="另一合成企业", 职位描述="", 最低月薪="面议")]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_skill_boundaries_negation_and_offsets(wb):
    text = "JavaScript，数字digital，掌握Java；无需Python；熟悉SQL和C++。"
    hits = wb.extract_skills(text)
    accepted = {hit["skill"] for hit in hits if hit["accepted"]}
    assert accepted == {"JavaScript", "Java", "SQL", "C++"}
    assert any(hit["skill"] == "Python" and not hit["accepted"] for hit in hits)
    assert all(text[h["start"] : h["end"]].lower() == h["surface"].lower() for h in hits)
    assert not wb.extract_skills("MySQL，digital，JavaScripted")


@pytest.mark.parametrize(
    "value, expected",
    [
        (("10000", "20000"), 15000),
        (("0", "1000"), None),
        (("20000", "10000"), None),
        (("NaN", "inf"), None),
        (("面议", ""), None),
    ],
)
def test_salary_interval_midpoint(wb, value, expected):
    assert wb.salary_midpoint(*value) == expected


def test_family_does_not_admit_hardware_or_sales(wb):
    assert wb.job_family("软件开发工程师") == "软件开发"
    assert wb.job_family("硬件开发工程师") is None
    assert wb.job_family("软件销售经理") is None
    assert wb.job_family("质量测试工程师") is None


def test_multiline_dedup_denominators_and_determinism(wb, tmp_path):
    path = make_input(tmp_path)
    left, right = tmp_path / "left", tmp_path / "right"
    wb.run({2026: path}, left)
    wb.run({2026: path}, right)
    a = json.loads((left / "summary.json").read_text(encoding="utf-8"))
    sample = a["years"]["2026"]
    assert sample["source_rows"] == 3
    assert sample["selected_before_dedup"] == 3
    assert sample["duplicate_rows"] == 1
    assert sample["selected_rows"] == 2
    assert sample["description_nonmissing"] == 1
    assert sample["salary_valid"] == 1
    with (left / "skills.csv").open(encoding="utf-8-sig", newline="") as stream:
        python = next(row for row in csv.DictReader(stream) if row["skill"] == "Python")
    assert float(python["share_all_jobs"]) == 0.5
    assert float(python["share_nonmissing_descriptions"]) == 1.0
    assert {p.name: p.read_bytes() for p in left.iterdir()} == {
        p.name: p.read_bytes() for p in right.iterdir()
    }
    with pytest.raises(FileExistsError, match="已存在"):
        wb.run({2026: path}, left)


def test_schema_failure_removes_temporary_output(wb, tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("职位名称\n合成岗位\n", encoding="utf-8")
    with pytest.raises(ValueError, match="缺少字段"):
        wb.run({2026: path}, tmp_path / "out")
    assert not (tmp_path / "out").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["bad.csv"]


def test_nonempty_trailing_column_is_counted_and_excluded(wb, tmp_path):
    path = make_input(tmp_path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    rows[1][-1] = "合成尾列异常"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream).writerows(rows)
    wb.run({2026: path}, tmp_path / "out")
    sample = json.loads((tmp_path / "out/summary.json").read_text(encoding="utf-8"))["years"][
        "2026"
    ]
    assert sample["trailing_nonempty_excluded"] == 1
    assert sample["source_rows"] == 3
    assert sample["selected_rows"] == 2


def test_evidence_offsets_refer_to_original_cell_including_whitespace(wb, tmp_path):
    path = make_input(tmp_path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    index = rows[0].index("职位描述")
    original = "  熟悉Python\n  "
    rows[1][index] = original
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream).writerows(rows)
    wb.run({2026: path}, tmp_path / "out")
    evidence = json.loads((tmp_path / "out/skill-evidence-local.json").read_text(encoding="utf-8"))
    hit = next(h for h in evidence["examples"] if h["csv_record_index"] == 1)
    assert original[hit["start"] : hit["end"]] == hit["surface"] == "Python"


def test_wrong_date_and_year_excluded_with_counts(wb, tmp_path):
    path = make_input(tmp_path, 2023)
    wb.run({2026: path}, tmp_path / "out")
    sample = json.loads((tmp_path / "out/summary.json").read_text(encoding="utf-8"))["years"][
        "2026"
    ]
    assert sample["selected_rows"] == 0
    assert sample["year_or_date_excluded"] == 3


def test_gap_is_placeholder_and_unknown_skills_refused(wb):
    plan = {
        "evidence_mode": "synthetic",
        "label": "示例占位",
        "courses": [
            {"course_id": "demo", "hours": 16, "skill_mentions": ["Python"]},
        ],
    }
    gap = wb.curriculum_gap(plan, {"Python": 0.5, "SQL": 0.25})
    assert gap["evidence_mode"] == "synthetic"
    assert gap["uncovered_mentions"] == ["SQL"]
    assert gap["not_a_learning_effect"] is True
    plan["courses"][0]["skill_mentions"] = ["invented"]
    with pytest.raises(ValueError, match="技能"):
        wb.curriculum_gap(plan, {"Python": 0.5})


@pytest.mark.parametrize("year", [2024, 2025])
def test_reviewed_annual_schemas_keep_own_semantics(wb, tmp_path, year):
    path = make_input(tmp_path, year)
    wb.run({year: path}, tmp_path / "out")
    sample = json.loads((tmp_path / "out/summary.json").read_text(encoding="utf-8"))["years"][
        str(year)
    ]
    assert sample["selected_rows"] == 2
    assert "平台" in sample["category_semantics"]["招聘类别"]
    assert sample["category_semantics"] != wb.SCHEMA_MEANING[2026]


def backtest_group(n, family, skill, salary):
    return {
        "n": n,
        "descriptions": n,
        "skills": {skill: n} if n else {},
        "structures": {"岗位族": {family: n}} if n else {},
        "salaries": [salary] * n if salary is not None else [],
    }


def test_retrospective_metrics_cutoff_zero_hits_and_baseline(wb):
    # 跨年泄漏会把这组手算误差压低：2026 全部同 2024，但必须被排除。
    a = backtest_group(2, "软件开发", "Python", 10000)
    b = backtest_group(2, "软件测试", "SQL", 20000)
    groups = {2016: a, 2023: a, 2024: b, 2025: b, 2026: b}
    report = wb.retrospective_backtest(groups)
    first, second = report["folds"]
    assert first["train_years"] == [2016, 2023]
    assert second["train_years"] == [2016, 2023, 2024]
    latest = first["methods"]["latest_year"]
    assert latest["family_mae"] == pytest.approx(0.4)
    assert latest["family_tvd"] == 1
    assert latest["skill_mae"] == pytest.approx(2 / 12)
    assert latest["skill_top5_overlap_n"] == 0
    assert latest["salary_absolute_error"] == 10000
    assert latest["salary_relative_error"] == 0.5
    assert first["actual"]["salary_coverage"] == 1
    assert first["actual"]["skills"]["Git"] == 0
    assert second["methods"]["latest_year"]["family_mae"] == 0
    mean = second["methods"]["annual_mean"]
    assert mean["family_mae"] == pytest.approx(4 / 15)
    assert mean["improves_baseline"]["family_mae"] is False
    assert mean["salary_absolute_error"] == pytest.approx(20000 / 3)


def test_retrospective_empty_samples_are_not_zero_error(wb):
    empty = backtest_group(0, "软件开发", "Python", None)
    valid = backtest_group(2, "软件开发", "Python", 10000)
    report = wb.retrospective_backtest({2023: empty, 2024: valid, 2025: empty})
    first, second = report["folds"]
    assert first["methods"]["latest_year"]["family_mae"] is None
    assert first["methods"]["latest_year"]["salary_absolute_error"] is None
    assert second["actual"]["salary_coverage"] is None
    assert second["methods"]["latest_year"]["skill_mae"] is None


def test_retrospective_zero_mentions_and_missing_salary_stay_visible(wb):
    group = backtest_group(2, "软件开发", "Python", None)
    group["skills"] = {}
    group["descriptions"] = 0
    report = wb.retrospective_backtest({2023: group, 2024: group, 2025: group})
    first = report["folds"][0]
    assert first["actual"]["skills"]["Python"] == 0
    assert first["actual"]["salary_coverage"] == 0
    metrics = first["methods"]["latest_year"]
    assert metrics["skill_mae"] == 0
    assert metrics["skill_top5_predicted"] == []
    assert metrics["skill_top5_overlap_n"] == 0
    assert metrics["salary_absolute_error"] is None


def test_backtest_run_requires_explicit_years_and_is_deterministic(wb, tmp_path):
    inputs = {year: make_input(tmp_path, year) for year in (2023, 2024, 2025)}
    for name in ("a", "b"):
        wb.run(inputs, tmp_path / name, backtest=True)
    assert (tmp_path / "a/backtest.json").read_bytes() == (
        tmp_path / "b/backtest.json"
    ).read_bytes()
    manifest = json.loads((tmp_path / "a/manifest.json").read_text(encoding="utf-8"))
    assert "backtest.json" in manifest["outputs"]
    with pytest.raises(ValueError, match="2023.*2024.*2025"):
        wb.run({2026: inputs[2025]}, tmp_path / "bad", backtest=True)
    assert not (tmp_path / "bad").exists()
