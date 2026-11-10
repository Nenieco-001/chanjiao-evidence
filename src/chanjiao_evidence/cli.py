"""Command-line interface. No credentials or external services required."""

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from . import __version__
from .curriculum import evaluate_curriculum
from .pipeline import _json_bytes, _rename_with_retry, run
from .reporting import _markdown_text


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


def _curriculum_markdown(report: dict) -> str:
    plan = report["curriculum"]

    def text(value):
        return _markdown_text("未提供" if value is None else value)

    lines = [
        "# 课程调整情景审议",
        f"{text(plan['school'])}，{text(plan['major'])}，{text(plan['program_version'])}。",
        "公开课程事实与决策假设分别输入。计算只覆盖所选课程，候选需教师审议。",
        f"原始材料 {text(plan['source']['url'])}",
        "## 候选动作与约束",
    ]
    for candidate in report["candidates"]:
        lines += [f"### {text(candidate['candidate_id'])}", f"计算状态 {text(candidate['status'])}"]
        for change in candidate["course_changes"]:
            lines.append(
                f"- {text(change['title'])}，课时 {text(change['hours_before'])} → "
                f"{text(change['hours_after'])}，学分 {text(change['credits_before'])} → "
                f"{text(change['credits_after'])}。{text(change['reason'])}"
            )
        lines.extend(f"- 约束问题 {text(item)}" for item in candidate["violations"])
        lines.extend(f"- 缺少输入 {text(item)}" for item in candidate["missing_inputs"])
    lines += ["## 效果证据", "就业率和起薪效果为 unidentified，尚缺以下识别依据。"]
    lines.extend(f"- {text(item)}" for item in report["employment_effect"]["missing_evidence"])
    lines += ["## 待核验约束"]
    lines.extend(f"- {text(item)}" for item in report["unverified_constraints"])
    lines += ["## 情景假设"]
    lines.extend(f"- {text(item)}" for item in report["assumptions"])
    lines += [
        "## 选择状态",
        text(report["selection_rule"]),
        "生成、评价、反思和修订日志保存在 JSON。",
    ]
    return "\n\n".join(lines) + "\n"


def _run_curriculum(args) -> None:
    destination = args.output.absolute()
    if os.path.lexists(destination):
        raise FileExistsError(f"输出目录已存在 {destination}，请换一个新路径")
    inputs = {"curriculum": args.plan.read_bytes(), "scenario": args.scenario.read_bytes()}
    report = evaluate_curriculum(json.loads(inputs["curriculum"]), json.loads(inputs["scenario"]))
    buffer = io.StringIO(newline="")
    fields = [
        "candidate_id",
        "status",
        "course_id",
        "title",
        "hours_before",
        "hours_after",
        "credits_before",
        "credits_after",
        "reason",
        "source_location",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for candidate in report["candidates"]:
        for change in candidate["course_changes"]:
            row = {key: change[key] for key in fields if key in change}
            row.update(candidate_id=candidate["candidate_id"], status=candidate["status"])
            for key, value in row.items():
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                    row[key] = "'" + value
            writer.writerow(row)
    outputs = {
        "curriculum-review.json": _json_bytes(report),
        "course-actions.csv": buffer.getvalue().encode("utf-8-sig"),
        "review.md": _curriculum_markdown(report).encode("utf-8"),
    }
    manifest = {
        "schema_version": 1,
        "package_version": __version__,
        "inputs": {name: hashlib.sha256(value).hexdigest() for name, value in inputs.items()},
        "outputs": {name: hashlib.sha256(value).hexdigest() for name, value in outputs.items()},
        "source_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(__file__).parent.glob("*.py"))
        },
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".curriculum-", dir=destination.parent))
    try:
        for name, content in outputs.items():
            (staged / name).write_bytes(content)
        (staged / "manifest.json").write_bytes(_json_bytes(manifest))
        if os.path.lexists(destination):
            raise FileExistsError(f"输出目录已存在 {destination}，请换一个新路径")
        _rename_with_retry(staged, destination)
        staged = None
    finally:
        if staged is not None:
            shutil.rmtree(staged)


def _strategy_markdown(report: dict) -> str:
    strategy = report["strategy"]
    effects = report["effects"]

    def text(value):
        return _markdown_text("未提供" if value is None else value)

    lines = [
        "# 培养方案研究审阅",
        "当前为审阅版。学生能力与就业效果未识别，候选需要学校审核。",
        "## 公开培养要求与路径检查",
        f"最低总学分 {text(strategy['program_requirements']['minimum_total_credits'])}。",
    ]
    for scenario in strategy["scenario_results"]:
        lines.append(f"### {text(scenario['scenario_id'])}")
        for candidate in scenario["candidates"]:
            lines.append(f"- {text(candidate['candidate_id'])}，{text(candidate['status'])}。")
            for change in candidate["course_changes"]:
                lines.append(
                    f"- {text(change['title'])}，学时 {text(change['hours_before'])} → "
                    f"{text(change['hours_after'])}，学分 {text(change['credits_before'])} → "
                    f"{text(change['credits_after'])}。"
                )
            for path in candidate["student_paths"]:
                lines.append(
                    f"- 路径 {text(path['path_id'])}，{text(path['status'])}，"
                    f"问题 {text(', '.join(path['violations']) or '已建模条件内未见违规')}。"
                )
    lines += ["## 反思与重新评价", text(strategy["termination_reason"])]
    for event in strategy["process_log"]:
        lines.append(text(json.dumps(event, ensure_ascii=False, sort_keys=True)))
    lines += ["## 方向分流与招生反馈"]
    lines.append(text(json.dumps(strategy["direction_policy"], ensure_ascii=False, sort_keys=True)))
    lines.append(text(json.dumps(strategy["admissions"], ensure_ascii=False, sort_keys=True)))
    lines += [
        "## 文献参照与三情景",
        "下面的数字属于原研究指标下的条件性参照，校内项目实践与校外实习的适用性尚待核验。",
        f"当前目标效果状态 {text(effects['target_effect']['status'])}。",
    ]
    for scenario in effects["scenarios"]:
        lines.append(
            f"- {text(scenario['scenario_id'])}，点值 {text(scenario['estimate'])}，"
            f"区间 {text(scenario['interval'])}，单位 {text(scenario['unit'])}。"
        )
    lines += ["## 风险与应对"]
    for risk in strategy["risk_matrix"]:
        lines.append(text(json.dumps(risk, ensure_ascii=False, sort_keys=True)))
    lines += ["## 正式提交缺项"]
    lines.extend(f"- {text(item)}" for item in report["unmet_requirements"])
    lines += ["课程事实、情景、完整过程和数值依据统一保存在 strategy-review.json。"]
    return "\n\n".join(lines) + "\n"


def _run_strategy(args) -> None:
    from .scenarios import evaluate_scenarios
    from .strategy import evaluate_strategy

    destination = args.output.absolute()
    if os.path.lexists(destination):
        raise FileExistsError(f"输出目录已存在 {destination}，请换一个新路径")
    inputs = {
        name: getattr(args, name).read_bytes()
        for name in ["plan", "program", "policy", "evidence", "effects"]
    }
    parsed = {name: json.loads(value) for name, value in inputs.items()}
    report = {
        "schema_version": 1,
        "status": "review_only",
        "strategy": evaluate_strategy(parsed["plan"], parsed["policy"], parsed["program"]),
        "effects": evaluate_scenarios(parsed["evidence"], parsed["effects"]),
        "unmet_requirements": [
            "T1.skills",
            "T1.directions",
            "T1.scale",
            "T2.school_approval_and_resources",
            "T2.admissions_calibration_and_long_run_stability",
            "T3.target_action_applicability_and_student_outcomes",
            "C.data_rights_and_official_test_set",
        ],
    }
    outputs = {
        "strategy-review.json": _json_bytes(report),
        "review.md": _strategy_markdown(report).encode("utf-8"),
    }
    manifest = {
        "schema_version": 1,
        "package_version": __version__,
        "inputs": {name: hashlib.sha256(value).hexdigest() for name, value in inputs.items()},
        "outputs": {name: hashlib.sha256(value).hexdigest() for name, value in outputs.items()},
        "source_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(__file__).parent.glob("*.py"))
        },
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".strategy-", dir=destination.parent))
    try:
        for name, content in outputs.items():
            (staged / name).write_bytes(content)
        (staged / "manifest.json").write_bytes(_json_bytes(manifest))
        if os.path.lexists(destination):
            raise FileExistsError(f"输出目录已存在 {destination}，请换一个新路径")
        _rename_with_retry(staged, destination)
        staged = None
    finally:
        if staged is not None:
            shutil.rmtree(staged)


def main(argv=None) -> int:
    _configure_utf8_output()
    parser = argparse.ArgumentParser(prog="chanjiao")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("run", help="分析改革面板并生成培养方案比较报告")
    for name in ["panel", "metadata", "plans", "output"]:
        command.add_argument(f"--{name}", type=Path, required=True)
    command.add_argument("--evidence", type=Path, help="可选的公开论文证据卡片 JSON")
    curriculum = commands.add_parser("curriculum", help="核对真实课程切片并生成调整情景")
    for name in ["plan", "scenario", "output"]:
        curriculum.add_argument(f"--{name}", type=Path, required=True)
    strategy = commands.add_parser("strategy", help="审查专业模块、政策机制与历史证据情景")
    for name in ["plan", "program", "policy", "evidence", "effects", "output"]:
        strategy.add_argument(f"--{name}", type=Path, required=True)
    bundle = commands.add_parser("bundle", help="按验收清单生成材料审阅包或正式提交包")
    for name in ["checklist", "materials", "output"]:
        bundle.add_argument(f"--{name}", type=Path, required=True)
    bundle.add_argument("--require-ready", action="store_true", help="缺少正式提交条件时拒绝打包")
    _add_warehouse_commands(commands)
    args = parser.parse_args(argv)
    try:
        if args.command == "strategy":
            _run_strategy(args)
            print(f"方案审阅已生成 {args.output / 'review.md'}")
            return 0
        if args.command == "bundle":
            from .submission import build_submission

            result = build_submission(
                args.checklist, args.materials, args.output, require_ready=args.require_ready
            )
            print(f"材料压缩包已生成 {args.output}")
            print(f"验收状态 {result['status']}，缺项 {len(result['unmet_requirements'])}")
            return 0
        if args.command == "curriculum":
            _run_curriculum(args)
            print(f"课程情景审议已生成 {args.output / 'review.md'}")
            return 0
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
