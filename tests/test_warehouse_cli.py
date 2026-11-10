import csv
import json
import zipfile

import pytest

from chanjiao_evidence.cli import main


@pytest.fixture
def recruitment_csv(tmp_path):
    path = tmp_path / "jobs.csv"
    header = [
        "企业名称",
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
        "招聘发布年份",
        "招聘结束年份",
        "来源",
    ]
    row = [
        "合成企业",
        "软件工程师",
        "北京",
        "海淀",
        "10000",
        "20000",
        "PRIVATE_TEXT_SENTINEL",
        "本科",
        "不限",
        "2",
        "全职",
        "技术",
        "合成",
        "北京",
        "海淀",
        "2026-01-01",
        "2026-03-01",
        "2026",
        "2026",
        "合成",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerow(row)
    return path


def test_zip_comparison_command_only_prints_summary_location(tmp_path, capsys):
    for name in ["left", "right"]:
        with zipfile.ZipFile(tmp_path / f"{name}.zip", "w") as archive:
            archive.writestr(f"{name}/policy.txt", "相同内容")
    destination = tmp_path / "comparison.json"
    assert (
        main(
            [
                "warehouse",
                "compare-zip",
                "--left",
                str(tmp_path / "left.zip"),
                "--right",
                str(tmp_path / "right.zip"),
                "--output",
                str(destination),
            ]
        )
        == 0
    )
    assert json.loads(destination.read_text(encoding="utf-8"))["identical"] is True
    assert str(destination) in capsys.readouterr().out


def test_warehouse_ingest_summary_and_export_normal_entry(tmp_path, recruitment_csv, capsys):
    database = tmp_path / "jobs.duckdb"
    shared = ["--database", str(database), "--dataset-id", "campus", "--version", "2026-a"]
    report = tmp_path / "import.json"
    assert (
        main(
            [
                "warehouse",
                "ingest",
                *shared,
                "--csv",
                str(recruitment_csv),
                "--expected-year",
                "2026",
                "--output",
                str(report),
            ]
        )
        == 0
    )
    assert json.loads(report.read_text(encoding="utf-8"))["row_count"] == 1
    retry = tmp_path / "retry.json"
    assert (
        main(
            [
                "warehouse",
                "ingest",
                *shared,
                "--csv",
                str(recruitment_csv),
                "--expected-year",
                "2026",
                "--output",
                str(retry),
            ]
        )
        == 0
    )
    assert json.loads(retry.read_text(encoding="utf-8"))["status"] == "skipped"
    summary = tmp_path / "summary.json"
    assert main(["warehouse", "summary", *shared, "--limit", "5", "--output", str(summary)]) == 0
    text = summary.read_text(encoding="utf-8")
    assert json.loads(text)["row_count"] == 1
    assert "PRIVATE_TEXT_SENTINEL" not in text
    parquet = tmp_path / "jobs.parquet"
    assert (
        main(
            [
                "warehouse",
                "export",
                *shared,
                "--destination",
                str(parquet),
                "--output",
                str(tmp_path / "export.json"),
            ]
        )
        == 0
    )
    assert parquet.is_file()
    assert "PRIVATE_TEXT_SENTINEL" not in capsys.readouterr().out


def test_existing_report_is_preserved_before_ingest(tmp_path, recruitment_csv):
    report = tmp_path / "report.json"
    report.write_text("preserve", encoding="utf-8")
    database = tmp_path / "jobs.duckdb"
    result = main(
        [
            "warehouse",
            "ingest",
            "--database",
            str(database),
            "--dataset-id",
            "campus",
            "--version",
            "a",
            "--csv",
            str(recruitment_csv),
            "--output",
            str(report),
        ]
    )
    assert result == 2
    assert report.read_text(encoding="utf-8") == "preserve"
    assert not database.exists()


def test_database_and_report_need_different_paths(tmp_path, recruitment_csv):
    destination = tmp_path / "same.duckdb"
    result = main(
        [
            "warehouse",
            "ingest",
            "--database",
            str(destination),
            "--dataset-id",
            "campus",
            "--version",
            "a",
            "--csv",
            str(recruitment_csv),
            "--output",
            str(destination),
        ]
    )
    assert result == 2
    assert not destination.exists()


def test_summary_limit_is_validated_at_cli_boundary(tmp_path):
    assert (
        main(
            [
                "warehouse",
                "summary",
                "--database",
                str(tmp_path / "jobs.duckdb"),
                "--dataset-id",
                "campus",
                "--version",
                "a",
                "--limit",
                "0",
                "--output",
                str(tmp_path / "summary.json"),
            ]
        )
        == 2
    )
