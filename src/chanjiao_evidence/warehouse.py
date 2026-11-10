"""本地招聘仓库，原始记录留在 DuckDB，公开接口只返回元数据与汇总。"""

import csv
import gzip
import hashlib
import tempfile
from contextlib import contextmanager
from pathlib import Path

import duckdb

RECRUITMENT_COLUMNS = (
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
)
STOCK_COLUMNS = ("股票简称", "关联股票代码", "与上市公司关系", "上市公司行业")
OPTIONAL_COLUMNS = ("来源平台",)
RAW_COLUMNS = RECRUITMENT_COLUMNS + STOCK_COLUMNS
REGISTRATION_FIELDS = (
    "dataset_id",
    "version",
    "source_path",
    "sha256",
    "source_size",
    "source_mtime_ns",
    "expected_year",
    "columns",
    "row_count",
)


def _identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_identity(dataset_id: str, version: str) -> None:
    for name, value in (("dataset_id", dataset_id), ("version", version)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} 不能为空，请指定数据集和明确版本。")


@contextmanager
def _connection(database: Path, *, read_only=False, memory_limit="512MB", threads=2):
    if read_only and not database.is_file():
        raise ValueError("数据库不存在，请先用 ingest 导入 CSV，再指定该数据库。")
    if not read_only:
        database.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = duckdb.connect(
            str(database),
            read_only=read_only,
            config={
                "memory_limit": memory_limit,
                "threads": threads,
                "temp_directory": str(database) + ".tmp",
                "preserve_insertion_order": False,
            },
        )
        try:
            yield connection
        finally:
            connection.close()
    except duckdb.Error as error:
        # DuckDB 的 CSV 异常可能带整行内容，接口只披露类别，原异常保留为 cause。
        raise ValueError(
            f"DuckDB 操作失败（{type(error).__name__}）。"
            "请检查 CSV 的 UTF-8 编码、引号和列数，以及内存配置、磁盘空间和数据库路径；"
            "未完成的导入已回滚。"
        ) from error


def _read_header(path: Path) -> list[str]:
    opener = gzip.open if path.name.lower().endswith(".csv.gz") else Path.open
    try:
        with opener(path, "rt", encoding="utf-8-sig", newline="") as stream:
            columns = next(csv.reader(stream, strict=True), [])
    except (csv.Error, UnicodeError, gzip.BadGzipFile, EOFError) as error:
        raise ValueError(
            "CSV 表头无法读取，请提供 UTF-8 编码、逗号分隔的 CSV 或 CSV.gz。"
        ) from error
    column_set = set(columns)
    accepted = (
        set(RECRUITMENT_COLUMNS),
        set(RAW_COLUMNS),
        set(RECRUITMENT_COLUMNS) - set(OPTIONAL_COLUMNS),
        set(RAW_COLUMNS) - set(OPTIONAL_COLUMNS),
    )
    if len(columns) != len(column_set) or column_set not in accepted:
        missing = sorted(set(RECRUITMENT_COLUMNS) - set(OPTIONAL_COLUMNS) - column_set)
        detail = "缺少字段 " + "、".join(missing) + "。" if missing else "存在重复或额外字段。"
        raise ValueError(
            f"CSV 表头必须为约定的 19/20 列或含股票信息的 23/24 列。{detail}"
            "请核对招聘字段名称并保留原始表头。"
        )
    return columns


def _create_schema(connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS recruitment_imports (
            dataset_id VARCHAR NOT NULL,
            version VARCHAR NOT NULL,
            source_path VARCHAR NOT NULL,
            sha256 VARCHAR NOT NULL,
            source_size BIGINT NOT NULL,
            source_mtime_ns BIGINT NOT NULL,
            expected_year INTEGER,
            columns VARCHAR[] NOT NULL,
            row_count BIGINT NOT NULL,
            PRIMARY KEY (dataset_id, version)
        )"""
    )
    raw_definitions = ", ".join(f"{_identifier(column)} VARCHAR" for column in RAW_COLUMNS)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS recruitment_raw "
        f"(dataset_id VARCHAR NOT NULL, version VARCHAR NOT NULL, {raw_definitions})"
    )
    typed = [
        "TRY_CAST(NULLIF(trim(raw.\"最低月薪\"), '') AS DOUBLE) AS salary_min",
        "TRY_CAST(NULLIF(trim(raw.\"最高月薪\"), '') AS DOUBLE) AS salary_max",
    ]
    for column, alias in (("招聘发布日期", "published_date"), ("招聘结束日期", "ended_date")):
        text = f"trim(raw.{_identifier(column)})"
        typed.append(
            f"CASE WHEN regexp_full_match({text}, '[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}') "
            f"THEN TRY_CAST({text} AS DATE) END AS {alias}"
        )
    for column, alias in (("招聘发布年份", "published_year"), ("招聘结束年份", "ended_year")):
        text = f"trim(raw.{_identifier(column)})"
        integer_part = f"TRY_CAST(split_part({text}, '.', 1) AS INTEGER)"
        typed.append(
            f"CASE WHEN regexp_full_match({text}, '[0-9]{{4}}([.]0+)?') "
            f"AND {integer_part} BETWEEN 1 AND 9999 "
            f"THEN {integer_part} END AS {alias}"
        )
    connection.execute(
        "CREATE OR REPLACE VIEW recruitment_typed AS SELECT raw.*, "
        "imports.source_path, imports.sha256 AS source_sha256, imports.expected_year, "
        + ", ".join(typed)
        + " FROM recruitment_raw AS raw JOIN recruitment_imports AS imports "
        "USING (dataset_id, version)"
    )


def _registration(connection, dataset_id: str, version: str) -> dict | None:
    fields = ", ".join(_identifier(field) for field in REGISTRATION_FIELDS)
    row = connection.execute(
        f"SELECT {fields} FROM recruitment_imports WHERE dataset_id = ? AND version = ?",
        [dataset_id, version],
    ).fetchone()
    if row is None:
        return None
    result = dict(zip(REGISTRATION_FIELDS, row, strict=True))
    result["missing_optional_columns"] = [
        column for column in OPTIONAL_COLUMNS if column not in result["columns"]
    ]
    return result


def _require_registration(connection, dataset_id: str, version: str) -> dict:
    registration = _registration(connection, dataset_id, version)
    if registration is None:
        raise ValueError("指定的数据集版本不存在，请核对 dataset_id/version 或先导入该版本。")
    return registration


def _check_unchanged(path: Path, original_stat) -> None:
    current = path.stat()
    if (current.st_size, current.st_mtime_ns) != (original_stat.st_size, original_stat.st_mtime_ns):
        raise ValueError("CSV 在处理期间发生变化，本次导入已取消；请等文件写入完成后重试。")


def ingest_recruitment(
    csv_path: Path,
    database: Path,
    dataset_id: str,
    version: str,
    *,
    expected_year: int | None = None,
    memory_limit: str = "512MB",
    threads: int = 2,
) -> dict:
    """事务导入一个完整 CSV，保留原值，同内容版本重试返回 skipped。"""
    _validate_identity(dataset_id, version)
    if type(threads) is not int or threads < 1:
        raise ValueError("threads 必须是正整数，请设置为 2 等有效线程数。")
    if expected_year is not None and (
        type(expected_year) is not int or not 1 <= expected_year <= 9999
    ):
        raise ValueError("expected_year 必须是 1–9999 的整数年份，跨年输入请省略此参数。")
    if not isinstance(memory_limit, str) or not memory_limit.strip():
        raise ValueError("memory_limit 必须是 DuckDB 内存大小，例如 512MB。")
    source = Path(csv_path).resolve()
    if not source.name.lower().endswith((".csv", ".csv.gz")):
        raise ValueError("输入格式必须是 .csv 或 .csv.gz，请先提取明确的招聘 CSV 成员。")
    original_stat = source.stat()
    digest = _sha256(source)
    _check_unchanged(source, original_stat)
    columns = _read_header(source)
    database = Path(database).resolve()
    with _connection(database, memory_limit=memory_limit, threads=threads) as connection:
        connection.execute("BEGIN TRANSACTION")
        try:
            _create_schema(connection)
            previous = _registration(connection, dataset_id, version)
            if previous is not None:
                if previous["sha256"] != digest:
                    raise ValueError(
                        "该数据集版本已有不同内容，请保留原版本并为新文件指定新版本名。"
                    )
                if previous["expected_year"] != expected_year:
                    raise ValueError("该版本已登记不同 expected_year，请使用原参数或指定新版本名。")
                _check_unchanged(source, original_stat)
                connection.execute("COMMIT")
                return {"status": "skipped", **previous}

            # 传递路径保留 .gz 自动识别，CSV 数据不经过 Python 全量读取。
            relation = connection.read_csv(
                str(source),
                header=True,
                auto_detect=False,
                columns={column: "VARCHAR" for column in columns},
                delimiter=",",
                quotechar='"',
                escapechar='"',
                encoding="utf-8",
                strict_mode=True,
                null_padding=False,
                ignore_errors=False,
                force_not_null=columns,
            )
            relation.create_view("incoming_recruitment", replace=True)
            projection = ", ".join(
                _identifier(column) if column in columns else "NULL" for column in RAW_COLUMNS
            )
            connection.execute(
                f"INSERT INTO recruitment_raw SELECT ?, ?, {projection} FROM incoming_recruitment",
                [dataset_id, version],
            )
            row_count = connection.execute(
                "SELECT count(*) FROM recruitment_raw WHERE dataset_id = ? AND version = ?",
                [dataset_id, version],
            ).fetchone()[0]
            _check_unchanged(source, original_stat)
            registration = {
                "dataset_id": dataset_id,
                "version": version,
                "source_path": str(source),
                "sha256": digest,
                "source_size": original_stat.st_size,
                "source_mtime_ns": original_stat.st_mtime_ns,
                "expected_year": expected_year,
                "columns": columns,
                "missing_optional_columns": [
                    column for column in OPTIONAL_COLUMNS if column not in columns
                ],
                "row_count": row_count,
            }
            placeholders = ", ".join("?" for _ in REGISTRATION_FIELDS)
            connection.execute(
                f"INSERT INTO recruitment_imports VALUES ({placeholders})",
                [registration[field] for field in REGISTRATION_FIELDS],
            )
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
    return {"status": "imported", **registration}


def _missing(column: str) -> str:
    field = _identifier(column)
    return f"({field} IS NULL OR trim({field}) = '')"


def _quality_conditions() -> dict[str, str]:
    conditions = {}
    for raw, field in (("最低月薪", "salary_min"), ("最高月薪", "salary_max")):
        conditions[field + "_parse"] = f"NOT {_missing(raw)} AND {field} IS NULL"
        conditions[field + "_nonfinite"] = f"NOT isfinite({field})"
        conditions[field + "_negative"] = f"isfinite({field}) AND {field} < 0"
    conditions["salary_range_reversed"] = (
        "isfinite(salary_min) AND isfinite(salary_max) "
        "AND salary_min >= 0 AND salary_max >= 0 AND salary_min > salary_max"
    )
    for raw, field in (
        ("招聘发布日期", "published_date"),
        ("招聘结束日期", "ended_date"),
        ("招聘发布年份", "published_year"),
        ("招聘结束年份", "ended_year"),
    ):
        conditions[field + "_invalid"] = f"NOT {_missing(raw)} AND {field} IS NULL"
    for prefix in ("published", "ended"):
        conditions[prefix + "_year_date_mismatch"] = f"{prefix}_year <> year({prefix}_date)"
    conditions["published_expected_year_mismatch"] = "published_year <> expected_year"
    conditions["published_date_expected_year_mismatch"] = "year(published_date) <> expected_year"
    conditions["date_range_reversed"] = "ended_date < published_date"
    return conditions


def summarize_recruitment(
    database: Path, dataset_id: str, version: str, *, limit: int = 10
) -> dict:
    """仅返回指定版本的聚合，不返回企业、岗位或描述原始记录。"""
    _validate_identity(dataset_id, version)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("limit 必须是 1–50 的整数，请缩小汇总条目数。")
    with _connection(Path(database).resolve(), read_only=True) as connection:
        registration = _require_registration(connection, dataset_id, version)
        source = "FROM recruitment_typed WHERE dataset_id = ? AND version = ?"
        parameters = [dataset_id, version]
        missing = {
            column: _missing(column)
            for column in registration["columns"] + registration["missing_optional_columns"]
        }
        invalid = _quality_conditions()
        normalization = {
            alias + "_integral_decimal": (
                f"regexp_full_match(trim({_identifier(column)}), '[0-9]{{4}}[.]0+') "
                f"AND {alias} IS NOT NULL"
            )
            for column, alias in (
                ("招聘发布年份", "published_year"),
                ("招聘结束年份", "ended_year"),
            )
        }
        expressions = ["count(*)"] + [
            f"count(*) FILTER (WHERE {condition})"
            for condition in (*missing.values(), *invalid.values(), *normalization.values())
        ]
        expressions += [
            "min(published_date)",
            "max(published_date)",
            "min(ended_date)",
            "max(ended_date)",
        ]
        values = connection.execute(
            "SELECT " + ", ".join(expressions) + " " + source, parameters
        ).fetchone()
        count_end = 1 + len(missing)
        invalid_end = count_end + len(invalid)
        normalization_end = invalid_end + len(normalization)
        raw_fields = ", ".join(_identifier(column) for column in registration["columns"])
        distinct_count = connection.execute(
            f"SELECT count(*) FROM (SELECT DISTINCT {raw_fields} "
            "FROM recruitment_raw WHERE dataset_id = ? AND version = ?)",
            parameters,
        ).fetchone()[0]
        result = {
            "dataset_id": dataset_id,
            "version": version,
            "source": registration,
            "expected_year": registration["expected_year"],
            "row_count": values[0],
            "exact_duplicate_rows": values[0] - distinct_count,
            "missing_counts": dict(zip(missing, values[1:count_end], strict=True)),
            "invalid_counts": dict(zip(invalid, values[count_end:invalid_end], strict=True)),
            "normalization_counts": dict(
                zip(normalization, values[invalid_end:normalization_end], strict=True)
            ),
            "date_range": dict(
                zip(
                    ("published_min", "published_max", "ended_min", "ended_max"),
                    (value.isoformat() if value else None for value in values[normalization_end:]),
                    strict=True,
                )
            ),
            "limit": limit,
        }
        for key, field, alias in (
            ("by_year", "published_year", "year"),
            ("by_city", "NULLIF(trim(\"工作城市\"), '')", "city"),
            ("by_education", "NULLIF(trim(\"学历要求\"), '')", "education"),
        ):
            rows = connection.execute(
                f"SELECT {field} AS value, count(*) AS count {source} "
                f"AND {field} IS NOT NULL GROUP BY value "
                "ORDER BY count DESC, value ASC LIMIT ?",
                parameters + [limit],
            ).fetchall()
            result[key] = [{alias: value, "count": count} for value, count in rows]
    return result


def export_recruitment(database: Path, dataset_id: str, version: str, destination: Path) -> dict:
    """将一个明确版本的原始字段、类型化字段和来源导出为新 Parquet 文件。"""
    _validate_identity(dataset_id, version)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError("导出路径已存在，请指定新的 Parquet 路径，已有文件不允许覆盖。")
    with _connection(Path(database).resolve(), read_only=True) as connection:
        registration = _require_registration(connection, dataset_id, version)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=f".{destination.name}.", dir=destination.parent
        ) as temp:
            temporary_file = Path(temp) / "data.parquet"
            connection.execute(
                "COPY (SELECT * FROM recruitment_typed WHERE dataset_id = ? AND version = ?) "
                "TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
                [dataset_id, version, str(temporary_file)],
            )
            digest = _sha256(temporary_file)
            size = temporary_file.stat().st_size
            temporary_file.rename(destination)
    return {
        "dataset_id": dataset_id,
        "version": version,
        "destination": str(destination),
        "row_count": registration["row_count"],
        "sha256": digest,
        "size": size,
        "compression": "ZSTD",
    }
