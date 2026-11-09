"""Command-line interface. No credentials or external services required."""

import argparse
import sys
from pathlib import Path

from .pipeline import run


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="chanjiao")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("run", help="analyze one panel and compare two plans")
    for name in ["panel", "metadata", "plans", "output"]:
        command.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(args.panel, args.metadata, args.plans, args.output)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"chanjiao: {error}", file=sys.stderr)
        return 2
    print(f"Report: {args.output / 'report.json'}")
    print(f"Evidence: {report['metadata']['evidence_mode']}")
    print(f"Selected plan: {report['planning']['selected_plan']}")
    return 0
