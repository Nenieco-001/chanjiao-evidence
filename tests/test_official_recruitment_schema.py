"""官方表头的合成回归，字段顺序经本机全量与2022年度RAR表头核对。"""

import codecs
import csv
import importlib.util
import json
from pathlib import Path

import duckdb
import pytest

from chanjiao_evidence.warehouse import export_recruitment, ingest_recruitment

FULL_FIELDS = (
    "企业名称",
    "股票简称",
    "关联股票代码",
    "与上市公司关系",
    "上市公司行业",
    "招聘发布年份",
    "招聘结束年份",
    "招聘岗位",
    "工作城市",
    "工作区域",
    "最低月薪",
    "最高月薪",
    "职位描述",
    "学历要求",
    "要求经验",
    "招聘人数",
    "招聘类别",
    "初级分类",
    "来源平台",
    "公司地点",
    "工作地点",
    "招聘发布日期",
    "招聘结束日期",
    "来源",
)
ANNUAL_2022_FIELDS = tuple(field for field in FULL_FIELDS if field != "来源平台")
SCRIPT = Path(__file__).resolve().parents[1] / "analysis/competition/workbench.py"


@pytest.fixture
def wb():
    spec = importlib.util.spec_from_file_location("official_schema_workbench", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_official_csv(path, fields, *, year=2026, changes=None):
    record = {
        "企业名称": "合成企业",
        "股票简称": "合成简称",
        "关联股票代码": "000001",
        "与上市公司关系": "合成关系",
        "上市公司行业": "软件和信息技术服务业",
        "招聘发布年份": f" {year}.0 ",
        "招聘结束年份": str(year),
        "招聘岗位": "软件工程师",
        "工作城市": "北京市",
        "最低月薪": "010000",
        "最高月薪": "020000",
        "职位描述": '  熟悉Python,\n掌握SQL及"测试"  ',
        "学历要求": "本科",
        "要求经验": "不限",
        "招聘人数": "若干",
        "招聘类别": "合成类别",
        "初级分类": "合成初类",
        "来源平台": "未用于工作台的合成平台列",
        "招聘发布日期": f"\t {year}-01-02 \t",
        "招聘结束日期": f"{year}-02-03",
        "来源": "合成来源",
    }
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for overrides in changes or [{}]:
            row = {**record, **overrides}
            writer.writerow({name: row.get(name, "") for name in fields})
    return path


@pytest.mark.parametrize("fields", [FULL_FIELDS, ANNUAL_2022_FIELDS], ids=["full24", "annual23"])
@pytest.mark.parametrize("reverse", [False, True], ids=["original_order", "reordered"])
def test_workbench_reads_both_header_shapes_by_name(wb, tmp_path, fields, reverse):
    """使用已支持的2026合成记录验证2022表头形状，年度语义准入另测。"""
    header = list(reversed(fields)) if reverse else list(fields)
    source = write_official_csv(tmp_path / "official.csv", header)
    assert source.read_bytes().startswith(codecs.BOM_UTF8)
    output = tmp_path / "result"
    summary = wb.run({2026: source}, output)["years"]["2026"]
    assert summary["columns"] == header
    assert len(header) in (23, 24)
    assert set(wb.FIELDS).issubset(header)
    assert "来源平台" not in wb.FIELDS
    assert summary["source_rows"] == summary["selected_rows"] == summary["salary_valid"] == 1
    assert summary["date_min"] == summary["date_max"] == "2026-01-02"
    assert summary["year_or_date_excluded"] == 0
    assert summary["platforms_selected"] == {"合成来源": 1}
    evidence = json.loads((output / "skill-evidence-local.json").read_bytes())
    assert {row["skill"] for row in evidence["examples"]} == {"Python", "SQL"}


def test_source_is_required_even_when_source_platform_is_present(wb, tmp_path):
    fields = [name for name in FULL_FIELDS if name != "来源"]
    source = write_official_csv(tmp_path / "missing-source.csv", fields)
    with pytest.raises(ValueError, match="缺少字段.*来源"):
        wb.run({2026: source}, tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_2022_year_still_requires_its_semantics_audit(wb, tmp_path):
    source = write_official_csv(tmp_path / "annual2022.csv", ANNUAL_2022_FIELDS, year=2022)
    with pytest.raises(ValueError, match="其他年份需先核验 schema"):
        wb.run({2022: source}, tmp_path / "result")
    assert not (tmp_path / "result").exists()


@pytest.mark.parametrize(
    "low,high,valid",
    [
        ("0", "20000", 0),
        ("", "20000", 0),
        ("10000", "0", 0),
        ("10000", "", 0),
        ("", "", 0),
        (" 010000 ", " 020000 ", 1),
    ],
)
def test_zero_and_blank_salary_keep_the_job_but_exclude_its_quote(wb, tmp_path, low, high, valid):
    source = write_official_csv(
        tmp_path / "salary.csv",
        ANNUAL_2022_FIELDS,
        changes=[{"最低月薪": low, "最高月薪": high}],
    )
    summary = wb.run({2026: source}, tmp_path / "result")["years"]["2026"]
    assert summary["selected_rows"] == 1
    assert summary["salary_valid"] == valid


def test_headcount_strings_do_not_weight_job_counts(wb, tmp_path):
    changes = [
        {"企业名称": f"合成企业{index}", "招聘人数": value}
        for index, value in enumerate(("若干", "3人", "0002", ""))
    ]
    source = write_official_csv(tmp_path / "headcounts.csv", FULL_FIELDS, changes=changes)
    summary = wb.run({2026: source}, tmp_path / "result")["years"]["2026"]
    assert summary["source_rows"] == summary["selected_rows"] == 4
    assert summary["salary_valid"] == 4


@pytest.mark.parametrize("fields", [FULL_FIELDS, ANNUAL_2022_FIELDS], ids=["full24", "annual23"])
def test_warehouse_import_export_keeps_stock_codes_and_raw_cleaning_inputs(tmp_path, fields):
    source = write_official_csv(
        tmp_path / "annual2022.csv",
        fields,
        year=2022,
        changes=[{"招聘发布日期": " 2022-01-02 "}],
    )
    database = tmp_path / "records.duckdb"
    result = ingest_recruitment(source, database, "synthetic-official", "v1", expected_year=2022)
    assert result["columns"] == list(fields)
    assert result["missing_optional_columns"] == ([] if len(fields) == 24 else ["来源平台"])
    with duckdb.connect(str(database), read_only=True) as connection:
        row = connection.execute(
            'SELECT "关联股票代码", typeof("关联股票代码"), "最低月薪", "招聘人数", '
            '"招聘发布日期", published_date, published_year FROM recruitment_typed'
        ).fetchone()
    assert row[:5] == ("000001", "VARCHAR", "010000", "若干", " 2022-01-02 ")
    assert row[5].isoformat() == "2022-01-02"
    assert row[6] == 2022
    output = tmp_path / "records.parquet"
    export_recruitment(database, "synthetic-official", "v1", output)
    with duckdb.connect() as connection:
        assert connection.execute(
            'SELECT "关联股票代码", typeof("关联股票代码") FROM read_parquet(?)', [str(output)]
        ).fetchall() == [("000001", "VARCHAR")]


def test_long_multiline_description_is_read_without_truncation(wb, tmp_path):
    description = "合成说明" * 40000 + ',"引号"\nPython'
    source = write_official_csv(
        tmp_path / "long-description.csv", FULL_FIELDS, changes=[{"职位描述": description}]
    )
    previous_limit = csv.field_size_limit(131072)
    try:
        output = tmp_path / "result"
        summary = wb.run({2026: source}, output)["years"]["2026"]
        assert summary["selected_rows"] == 1
        evidence = json.loads((output / "skill-evidence-local.json").read_bytes())
        hit = next(row for row in evidence["examples"] if row["skill"] == "Python")
        assert description[hit["start"] : hit["end"]] == "Python"
    finally:
        csv.field_size_limit(previous_limit)
