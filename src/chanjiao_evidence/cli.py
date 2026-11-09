"""Command-line interface. No credentials or external services required."""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from .pipeline import _json_bytes, _rename_with_retry, run


def _configure_utf8_output() -> None:
    """Keep Chinese messages printable when output is redirected on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            continue


def _add_warehouse_commands(commands) -> None:
    warehouse = commands.add_parser("warehouse", help="本地数据版本核验、入库与聚合查询")
    actions = warehouse.add_subparsers(dest="warehouse_action", required=True)
    compare = actions.add_parser("compare-zip", help="核验并比较两个 ZIP 副本")
    compare.add_argument("--left", type=Path, required=True)
    compare.add_argument("--right", type=Path, required=True)
    listing = actions.add_parser("list-rar", help="只读取 RAR 成员目录")
    unpack = actions.add_parser("unpack", help="完整校验并提取一个明确的 CSV 成员")
    for action in [listing, unpack]:
        action.add_argument("--archive", type=Path, required=True)
        action.add_argument("--unrar", type=Path, required=True, help="本机 UnRAR 可执行文件")
    unpack.add_argument("--member", required=True)
    unpack.add_argument("--destination", type=Path, required=True)
    ingest = actions.add_parser("ingest", help="将一个 CSV 版本导入 DuckDB")
    summary = actions.add_parser("summary", help="输出限定数量的质量和分组汇总")
    export = actions.add_parser("export", help="将明确的数据版本导出为 Parquet")
    for action in [ingest, summary, export]:
        action.add_argument("--database", type=Path, required=True)
        action.add_argument("--dataset-id", required=True)
        action.add_argument("--version", required=True)
    ingest.add_argument("--csv", type=Path, required=True)
    ingest.add_argument("--expected-year", type=int)
    ingest.add_argument("--memory-limit", default="512MB")
    ingest.add_argument("--threads", type=int, default=2)
    summary.add_argument("--limit", type=int, default=10)
    export.add_argument("--destination", type=Path, required=True)
    for action in [compare, listing, unpack, ingest, summary, export]:
        action.add_argument("--output", type=Path, required=True, help="新建的元数据 JSON 路径")


def _write_warehouse_report(destination: Path, result: dict) -> None:
    content = _json_bytes(result)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".warehouse-report-", dir=destination.parent
    ) as directory:
        staged = Path(directory) / "report.json"
        staged.write_bytes(content)
        if os.path.lexists(destination):
            raise FileExistsError(f"报告已存在 {destination}，请换一个输出路径")
        _rename_with_retry(staged, destination)


def _run_warehouse(args) -> dict:
    from .archives import compare_zip_archives, extract_rar_member, list_rar_members
    from .warehouse import export_recruitment, ingest_recruitment, summarize_recruitment

    destination = args.output.absolute()
    if os.path.lexists(destination):
        raise FileExistsError(f"报告已存在 {destination}，请换一个输出路径")
    for name in ["database", "destination"]:
        other = getattr(args, name, None)
        if other is not None and other.absolute() == destination:
            raise ValueError("数据库或数据文件与元数据报告需要不同路径，请修改 --output")
    if args.warehouse_action == "summary" and not 1 <= args.limit <= 50:
        raise ValueError("汇总 --limit 需要在 1–50 之间，请限制输出数量")
    match args.warehouse_action:
        case "compare-zip":
            return compare_zip_archives(args.left, args.right)
        case "list-rar":
            members = list_rar_members(args.archive, args.unrar)
            return {
                "archive": str(args.archive),
                "member_count": len(members),
                "members": members,
                "integrity": "headers_only",
            }
        case "unpack":
            return extract_rar_member(args.archive, args.member, args.destination, args.unrar)
        case "ingest":
            return ingest_recruitment(
                args.csv,
                args.database,
                args.dataset_id,
                args.version,
                expected_year=args.expected_year,
                memory_limit=args.memory_limit,
                threads=args.threads,
            )
        case "summary":
            return summarize_recruitment(
                args.database, args.dataset_id, args.version, limit=args.limit
            )
        case "export":
            return export_recruitment(
                args.database, args.dataset_id, args.version, args.destination
            )
    raise ValueError("请选择 warehouse 子命令，运行 warehouse --help 查看用法")


def main(argv=None) -> int:
    _configure_utf8_output()
    parser = argparse.ArgumentParser(prog="chanjiao")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("run", help="分析改革面板并生成培养方案比较报告")
    for name in ["panel", "metadata", "plans", "output"]:
        command.add_argument(f"--{name}", type=Path, required=True)
    command.add_argument("--evidence", type=Path, help="可选的公开论文证据卡片 JSON")
    _add_warehouse_commands(commands)
    args = parser.parse_args(argv)
    try:
        if args.command == "warehouse":
            result = _run_warehouse(args)
            _write_warehouse_report(args.output, result)
            print(f"数据处理结果已写入 {args.output}")
            return 0
        report = run(
            args.panel, args.metadata, args.plans, args.output, evidence_path=args.evidence
        )
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"chanjiao: {error}", file=sys.stderr)
        return 2
    print(f"中文报告已生成 {args.output / 'report.html'}")
    print(f"数据标识 {report['metadata']['evidence_mode']}")
    print(f"当前选择 {report['planning']['selected_plan']}")
    return 0
