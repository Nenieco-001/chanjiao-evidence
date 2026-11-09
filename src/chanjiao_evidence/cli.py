"""Command-line interface. No credentials or external services required."""

import argparse
import sys
from pathlib import Path

from .pipeline import run


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


def main(argv=None) -> int:
    _configure_utf8_output()
    parser = argparse.ArgumentParser(prog="chanjiao")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("run", help="分析改革面板并生成培养方案比较报告")
    for name in ["panel", "metadata", "plans", "output"]:
        command.add_argument(f"--{name}", type=Path, required=True)
    command.add_argument("--evidence", type=Path, help="可选的公开论文证据卡片 JSON")
    args = parser.parse_args(argv)
    try:
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
