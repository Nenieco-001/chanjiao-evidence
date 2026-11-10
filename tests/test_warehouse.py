import csv
import gzip
import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from chanjiao_evidence.warehouse import (
    export_recruitment,
    ingest_recruitment,
    summarize_recruitment,
)

HEADERS = [
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
EXTRA_HEADERS = ["股票简称", "关联股票代码", "与上市公司关系", "上市公司行业"]


def write_csv(path, rows, headers=HEADERS):
    opener = gzip.open if path.suffix == ".gz" else Path.open
    with opener(path, "wt", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        for changes in rows:
            row = dict.fromkeys(headers, "")
            row.update(
                {
                    "企业名称": "合成企业",
                    "招聘岗位": "合成岗位",
                    "工作城市": "甲城",
                    "最低月薪": "08000",
                    "最高月薪": "12000",
                    "职位描述": "合成描述",
                    "学历要求": "本科",
                    "招聘发布日期": "2026-01-02",
                    "招聘结束日期": "2026-02-03",
                    "招聘发布年份": "2026",
                    "招聘结束年份": "2026",
                }
            )
            row.update(changes)
            writer.writerow(row)
    return path


def test_ingest_preserves_bom_multiline_raw_values_and_source(tmp_path):
    source = write_csv(tmp_path / "input.csv", [{"职位描述": '引号"和逗号,\n第二行'}])
    database = tmp_path / "store.duckdb"
    result = ingest_recruitment(source, database, "synthetic", "v1", expected_year=2026)
    assert result["status"] == "imported"
    assert result["row_count"] == 1
    assert result["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert result["source_path"] == str(source.resolve())
    assert result["columns"] == HEADERS
    with duckdb.connect(str(database), read_only=True) as connection:
        row = connection.execute(
            'SELECT "职位描述", "最低月薪", "工作区域", salary_min, published_date '
            "FROM recruitment_typed"
        ).fetchone()
    assert row[:4] == ('引号"和逗号,\n第二行', "08000", "", 8000)
    assert row[4].isoformat() == "2026-01-02"
    assert "合成描述" not in json.dumps(result, ensure_ascii=False)


def test_twenty_and_twenty_four_columns_and_version_isolation(tmp_path):
    database = tmp_path / "store.duckdb"
    first = write_csv(tmp_path / "small.csv", [{}])
    second = write_csv(
        tmp_path / "large.csv",
        [{"关联股票代码": "000001"}, {"工作城市": "乙城"}],
        HEADERS + EXTRA_HEADERS,
    )
    ingest_recruitment(first, database, "synthetic", "v1")
    ingest_recruitment(second, database, "synthetic", "v2")
    assert summarize_recruitment(database, "synthetic", "v1")["row_count"] == 1
    assert summarize_recruitment(database, "synthetic", "v2")["row_count"] == 2
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute(
            'SELECT "关联股票代码" FROM recruitment_raw WHERE version = ? ORDER BY "关联股票代码"',
            ["v1"],
        ).fetchall() == [(None,)]
        assert connection.execute(
            'SELECT "关联股票代码" FROM recruitment_raw WHERE version = ? ORDER BY "关联股票代码"',
            ["v2"],
        ).fetchall() == [("",), ("000001",)]


@pytest.mark.parametrize("stock", [False, True])
def test_annual_input_without_source_platform_preserves_actual_columns(tmp_path, stock):
    headers = [column for column in HEADERS if column != "来源平台"]
    if stock:
        headers += EXTRA_HEADERS
    source = write_csv(tmp_path / "annual.csv", [{}], headers)
    database = tmp_path / "store.duckdb"
    result = ingest_recruitment(source, database, "synthetic", "annual")
    assert result["columns"] == headers
    assert result["missing_optional_columns"] == ["来源平台"]
    assert summarize_recruitment(database, "synthetic", "annual")["missing_counts"]["来源平台"] == 1
    repeated = ingest_recruitment(source, database, "synthetic", "annual")
    assert repeated["missing_optional_columns"] == ["来源平台"]
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute('SELECT "来源平台" FROM recruitment_raw').fetchone() == (None,)


def test_same_version_retries_skip_and_changed_content_is_rejected(tmp_path):
    source = write_csv(tmp_path / "input.csv", [{}])
    database = tmp_path / "store.duckdb"
    ingest_recruitment(source, database, "synthetic", "v1", expected_year=2026)
    assert (
        ingest_recruitment(source, database, "synthetic", "v1", expected_year=2026)["status"]
        == "skipped"
    )
    write_csv(source, [{"工作城市": "乙城"}])
    with pytest.raises(ValueError, match="版本|version"):
        ingest_recruitment(source, database, "synthetic", "v1")
    assert summarize_recruitment(database, "synthetic", "v1")["row_count"] == 1


def test_malformed_csv_rolls_back_rows_and_registration(tmp_path):
    database = tmp_path / "store.duckdb"
    source = write_csv(tmp_path / "good.csv", [{}])
    ingest_recruitment(source, database, "synthetic", "v1")
    broken = write_csv(tmp_path / "bad.csv", [{}] * 5)
    with broken.open("a", encoding="utf-8") as stream:
        stream.write('"不得出现在异常消息里的合成描述,broken\n')
    with pytest.raises(ValueError) as caught:
        ingest_recruitment(broken, database, "synthetic", "v2")
    assert "不得出现在异常消息" not in str(caught.value)
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM recruitment_imports").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM recruitment_raw").fetchone() == (1,)
    write_csv(broken, [{}])
    assert ingest_recruitment(broken, database, "synthetic", "v2")["row_count"] == 1


@pytest.mark.parametrize(
    "headers", [HEADERS[:-1], HEADERS[:-1] + ["企业名称"], HEADERS + ["未知字段"], []]
)
def test_rejects_missing_duplicate_and_unexpected_headers(tmp_path, headers):
    source = tmp_path / "input.csv"
    with source.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerow(headers)
    with pytest.raises(ValueError, match="表头|字段|列"):
        ingest_recruitment(source, tmp_path / "store.duckdb", "synthetic", "v1")


def test_gzip_hash_and_literal_null_strings_are_preserved(tmp_path):
    source = write_csv(tmp_path / "input.csv.gz", [{"工作区域": "NULL", "要求经验": "NA"}])
    database = tmp_path / "store.duckdb"
    result = ingest_recruitment(source, database, "synthetic", "v1")
    assert result["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute(
            'SELECT "工作区域", "要求经验" FROM recruitment_raw'
        ).fetchone() == (
            "NULL",
            "NA",
        )


def test_summary_counts_quality_without_silently_fixing_values(tmp_path):
    source = write_csv(
        tmp_path / "input.csv",
        [
            {},
            {},
            {"最低月薪": "NaN", "最高月薪": "inf", "招聘发布日期": "2026-02-30"},
            {"最低月薪": "-1", "最高月薪": "no", "招聘结束日期": "2026-1-3"},
            {
                "最低月薪": "200",
                "最高月薪": "100",
                "招聘发布年份": "2025",
                "招聘结束年份": "2026.5",
                "招聘结束日期": "2025-12-31",
            },
            {
                "最低月薪": "",
                "最高月薪": " ",
                "招聘发布日期": "2026-01-02 10:00:00",
                "招聘发布年份": "2026.5",
                "工作城市": "",
            },
        ],
    )
    database = tmp_path / "store.duckdb"
    ingest_recruitment(source, database, "synthetic", "v1", expected_year=2026)
    result = summarize_recruitment(database, "synthetic", "v1")
    assert result["row_count"] == 6
    assert result["exact_duplicate_rows"] == 1
    assert result["missing_counts"]["最低月薪"] == 1
    assert result["missing_counts"]["工作城市"] == 1
    invalid = result["invalid_counts"]
    assert invalid["salary_min_nonfinite"] == 1
    assert invalid["salary_max_nonfinite"] == 1
    assert invalid["salary_min_negative"] == 1
    assert invalid["salary_max_parse"] == 1
    assert invalid["salary_range_reversed"] == 1
    assert invalid["published_date_invalid"] == 2
    assert invalid["ended_date_invalid"] == 1
    assert invalid["published_year_invalid"] == 1
    assert invalid["ended_year_invalid"] == 1
    assert invalid["published_year_date_mismatch"] == 1
    assert invalid["published_expected_year_mismatch"] == 1
    assert invalid["date_range_reversed"] == 1
    assert result["date_range"] == {
        "published_min": "2026-01-02",
        "published_max": "2026-01-02",
        "ended_min": "2025-12-31",
        "ended_max": "2026-02-03",
    }
    assert result["by_year"] == [{"year": 2026, "count": 4}, {"year": 2025, "count": 1}]
    text = json.dumps(result, ensure_ascii=False, allow_nan=False)
    assert "合成描述" not in text
    assert "合成企业" not in text
    assert "合成岗位" not in text


def test_summary_limit_and_stable_tie_order(tmp_path):
    source = write_csv(tmp_path / "input.csv", [{"工作城市": city} for city in ["乙", "甲", "丙"]])
    database = tmp_path / "store.duckdb"
    ingest_recruitment(source, database, "synthetic", "v1")
    first = summarize_recruitment(database, "synthetic", "v1", limit=2)
    assert first["by_city"] == [{"city": "丙", "count": 1}, {"city": "乙", "count": 1}]
    assert first == summarize_recruitment(database, "synthetic", "v1", limit=2)
    for limit in [0, 51, True, 1.5]:
        with pytest.raises(ValueError, match="limit|1.*50"):
            summarize_recruitment(database, "synthetic", "v1", limit=limit)


def test_export_parquet_retains_raw_typed_provenance_and_refuses_overwrite(tmp_path):
    source = write_csv(tmp_path / "in'put.csv", [{"最低月薪": "08000"}])
    database = tmp_path / "store.duckdb"
    dataset_id = "synthetic' OR true --"
    ingest_recruitment(source, database, dataset_id, "v'1")
    destination = tmp_path / "out'put.parquet"
    result = export_recruitment(database, dataset_id, "v'1", destination)
    assert result["row_count"] == 1
    assert result["compression"] == "ZSTD"
    assert result["sha256"] == hashlib.sha256(destination.read_bytes()).hexdigest()
    with duckdb.connect() as connection:
        row = connection.execute(
            'SELECT "最低月薪", salary_min, dataset_id, version, source_sha256 '
            "FROM read_parquet(?)",
            [str(destination)],
        ).fetchone()
    assert row == (
        "08000",
        8000,
        dataset_id,
        "v'1",
        hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    original = destination.read_bytes()
    with pytest.raises(ValueError, match="存在|覆盖"):
        export_recruitment(database, dataset_id, "v'1", destination)
    assert destination.read_bytes() == original
    assert not list(tmp_path.glob(".out'put.parquet.*"))


def test_missing_version_does_not_create_database_or_export(tmp_path):
    database = tmp_path / "missing.duckdb"
    with pytest.raises(ValueError, match="数据库|不存在"):
        summarize_recruitment(database, "synthetic", "v1")
    assert not database.exists()
    source = write_csv(tmp_path / "input.csv", [{}])
    ingest_recruitment(source, database, "synthetic", "v1")
    with pytest.raises(ValueError, match="版本|version"):
        summarize_recruitment(database, "synthetic", "missing")
    destination = tmp_path / "missing.parquet"
    with pytest.raises(ValueError, match="版本|version"):
        export_recruitment(database, "synthetic", "missing", destination)
    assert not destination.exists()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"threads": 0},
        {"threads": True},
        {"memory_limit": "bad"},
        {"expected_year": 2026.5},
        {"expected_year": True},
    ],
)
def test_ingest_rejects_invalid_execution_options(tmp_path, kwargs):
    source = write_csv(tmp_path / "input.csv", [{}])
    with pytest.raises(ValueError):
        ingest_recruitment(source, tmp_path / "store.duckdb", "synthetic", "v1", **kwargs)


def test_changed_source_during_import_rolls_back(tmp_path, monkeypatch):
    from chanjiao_evidence import warehouse

    source = write_csv(tmp_path / "input.csv", [{}])
    database = tmp_path / "store.duckdb"
    ingest_recruitment(source, database, "synthetic", "v1")
    original_read_header = warehouse._read_header

    def change_after_header(path):
        header = original_read_header(path)
        write_csv(path, [{}, {"工作城市": "外部写入的合成变化"}])
        return header

    monkeypatch.setattr(warehouse, "_read_header", change_after_header)
    with pytest.raises(ValueError, match="变化"):
        ingest_recruitment(source, database, "synthetic", "v2")
    assert summarize_recruitment(database, "synthetic", "v1")["row_count"] == 1
    with pytest.raises(ValueError, match="版本"):
        summarize_recruitment(database, "synthetic", "v2")


def test_export_failure_cleans_temporary_parquet(tmp_path, monkeypatch):
    from chanjiao_evidence import warehouse

    source = write_csv(tmp_path / "input.csv", [{}])
    database = tmp_path / "store.duckdb"
    ingest_recruitment(source, database, "synthetic", "v1")
    destination = tmp_path / "output.parquet"

    def failing_hash(path):
        assert path.is_file()
        raise OSError("模拟文件读取失败")

    monkeypatch.setattr(warehouse, "_sha256", failing_hash)
    with pytest.raises(OSError, match="模拟文件读取失败"):
        export_recruitment(database, "synthetic", "v1", destination)
    assert not destination.exists()
    assert not list(tmp_path.glob(".output.parquet.*"))


def test_retry_with_changed_expected_year_requires_new_version(tmp_path):
    source = write_csv(tmp_path / "input.csv", [{}])
    database = tmp_path / "store.duckdb"
    ingest_recruitment(source, database, "synthetic", "v1", expected_year=2026)
    with pytest.raises(ValueError, match="expected_year"):
        ingest_recruitment(source, database, "synthetic", "v1", expected_year=2025)
    assert summarize_recruitment(database, "synthetic", "v1")["expected_year"] == 2026


def test_integral_decimal_years_are_normalized_without_rounding_or_changing_raw(tmp_path):
    source = write_csv(
        tmp_path / "input.csv",
        [
            {"招聘发布年份": "2026", "招聘结束年份": "2026.0"},
            {"招聘发布年份": "2026.0", "招聘结束年份": "2026.00"},
            {"招聘发布年份": "2026.00", "招聘结束年份": "2026.5"},
            {"招聘发布年份": "2026.5", "招聘结束年份": "2026"},
            {"招聘发布年份": "0000.0", "招聘结束年份": "202.0"},
        ],
    )
    database = tmp_path / "store.duckdb"
    ingest_recruitment(source, database, "synthetic", "v1", expected_year=2026)
    with duckdb.connect(str(database), read_only=True) as connection:
        rows = connection.execute(
            'SELECT "招聘发布年份", "招聘结束年份", published_year, ended_year '
            "FROM recruitment_typed"
        ).fetchall()
    assert set(rows) == {
        ("2026", "2026.0", 2026, 2026),
        ("2026.0", "2026.00", 2026, 2026),
        ("2026.00", "2026.5", 2026, None),
        ("2026.5", "2026", None, 2026),
        ("0000.0", "202.0", None, None),
    }
    summary = summarize_recruitment(database, "synthetic", "v1")
    assert summary["normalization_counts"] == {
        "published_year_integral_decimal": 2,
        "ended_year_integral_decimal": 2,
    }
    assert summary["invalid_counts"]["published_year_invalid"] == 2
    assert summary["invalid_counts"]["ended_year_invalid"] == 2
    assert summary["by_year"] == [{"year": 2026, "count": 3}]


def test_idempotent_retry_refreshes_legacy_view_without_reinserting_rows(tmp_path):
    source = write_csv(
        tmp_path / "input.csv", [{"招聘发布年份": "2026.0", "招聘结束年份": "2026.00"}]
    )
    database = tmp_path / "store.duckdb"
    original = ingest_recruitment(source, database, "synthetic", "v1", expected_year=2026)
    with duckdb.connect(str(database)) as connection:
        # 模拟已落盘的旧视图，旧版本只接受四位整数字符串。
        connection.execute(
            """CREATE OR REPLACE VIEW recruitment_typed AS
            SELECT raw.*, imports.source_path, imports.sha256 AS source_sha256,
                imports.expected_year,
                TRY_CAST(raw."最低月薪" AS DOUBLE) AS salary_min,
                TRY_CAST(raw."最高月薪" AS DOUBLE) AS salary_max,
                TRY_CAST(raw."招聘发布日期" AS DATE) AS published_date,
                TRY_CAST(raw."招聘结束日期" AS DATE) AS ended_date,
                CASE WHEN regexp_full_match(raw."招聘发布年份", '[0-9]{4}')
                    THEN TRY_CAST(raw."招聘发布年份" AS INTEGER) END AS published_year,
                CASE WHEN regexp_full_match(raw."招聘结束年份", '[0-9]{4}')
                    THEN TRY_CAST(raw."招聘结束年份" AS INTEGER) END AS ended_year
            FROM recruitment_raw AS raw JOIN recruitment_imports AS imports
            USING (dataset_id, version)"""
        )
        assert connection.execute(
            "SELECT published_year, ended_year FROM recruitment_typed"
        ).fetchone() == (None, None)
    retried = ingest_recruitment(source, database, "synthetic", "v1", expected_year=2026)
    assert retried == {**original, "status": "skipped"}
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute(
            "SELECT published_year, ended_year FROM recruitment_typed"
        ).fetchone() == (2026, 2026)
        assert connection.execute("SELECT count(*) FROM recruitment_raw").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM recruitment_imports").fetchone() == (1,)
    assert summarize_recruitment(database, "synthetic", "v1")["normalization_counts"] == {
        "published_year_integral_decimal": 1,
        "ended_year_integral_decimal": 1,
    }
