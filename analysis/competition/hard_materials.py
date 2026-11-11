"""Generate reproducible four-task evidence from the repository's public JSON inputs."""

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import tempfile
from pathlib import Path

from chanjiao_evidence.hard_materials import evaluate_hard_materials
from chanjiao_evidence.pipeline import _json_bytes, _rename_with_retry

INPUT_PATHS = {
    "plan": "data/curricula/official-cs-extract.json",
    "program": "data/curricula/cufe-2025-program.json",
    "policy": "data/examples/program-policy.json",
    "demand": "data/examples/demand-beijing-2026.json",
    "comparison": "data/examples/comparison-assumptions.json",
    "evidence": "data/evidence/course-projects.json",
    "effects": "data/examples/project-effect-scenarios.json",
    "actions": "data/examples/hard-materials-actions.json",
}


def csv_bytes(rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def generate(root, output):
    root = Path(root).resolve()
    output = Path(output).absolute()
    if os.path.lexists(output):
        raise FileExistsError("输出路径已存在，请指定新目录保留既有材料")
    inputs = {role: (root / name).read_bytes() for role, name in INPUT_PATHS.items()}
    result = evaluate_hard_materials(
        **{role: json.loads(content) for role, content in inputs.items()}
    )
    action_rows, constraint_rows = [], []
    for candidate in result["course_candidates"]:
        for change in candidate["course_changes"]:
            action_rows.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "scenario_id": candidate["scenario_id"],
                    "candidate_status": candidate["status"],
                    "approval_status": candidate["approval_status"],
                    **change,
                }
            )
        for path in candidate["student_paths"]:
            for module, minimum in result["module_minimum_credits"].items():
                constraint_rows.append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "candidate_status": candidate["status"],
                        "path_id": path["path_id"],
                        "module": module,
                        "minimum_credits": minimum,
                        "credits_before": path["module_credits_before"][module],
                        "credits_after": path["module_credits_after"][module],
                        "module_pass": path["module_credits_after"][module] >= minimum,
                        "total_credits_after": path["total_credits_after"],
                        "minimum_total_credits": result["minimum_total_credits"],
                        "path_status": path["status"],
                        "violations": " | ".join(path["violations"]),
                    }
                )
    risk_rows = [
        {
            **row,
            "probability_range": json.dumps(row["probability_range"]),
            "related_scenarios": " | ".join(row["related_scenarios"]),
        }
        for row in result["risks"]
    ]
    outputs = {
        "hard-materials.json": _json_bytes(result),
        "course-actions.csv": csv_bytes(
            action_rows,
            [
                "candidate_id",
                "scenario_id",
                "candidate_status",
                "approval_status",
                "action_type",
                "course_id",
                "title",
                "module_id",
                "hours_before",
                "hours_after",
                "credits_before",
                "credits_after",
                "evidence_kind",
                "source_location",
            ],
        ),
        "path-constraints.csv": csv_bytes(
            constraint_rows,
            [
                "candidate_id",
                "candidate_status",
                "path_id",
                "module",
                "minimum_credits",
                "credits_before",
                "credits_after",
                "module_pass",
                "total_credits_after",
                "minimum_total_credits",
                "path_status",
                "violations",
            ],
        ),
        "skill-carriers.csv": csv_bytes(
            result["skill_carriers"],
            [
                "scenario_id",
                "skill",
                "course_id",
                "title",
                "evidence_kind",
                "requirement",
                "source_location",
                "proposal",
            ],
        ),
        "risk-matrix.csv": csv_bytes(
            risk_rows,
            [
                "risk_id",
                "action_id",
                "related_scenarios",
                "impact",
                "owner",
                "timing",
                "indicator",
                "threshold",
                "response",
                "probability_status",
                "probability_range",
                "evidence_mode",
            ],
        ),
    }
    sources = [
        "analysis/competition/hard_materials.py",
        *sorted(
            path.relative_to(root).as_posix()
            for path in (root / "src/chanjiao_evidence").glob("*.py")
        ),
    ]
    manifest = {
        "schema_version": 1,
        "input_paths": INPUT_PATHS,
        "inputs": {role: hashlib.sha256(content).hexdigest() for role, content in inputs.items()},
        "outputs": {name: hashlib.sha256(content).hexdigest() for name, content in outputs.items()},
        "source_sha256": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources
        },
    }
    outputs["manifest.json"] = _json_bytes(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".hard-materials-", dir=output.parent))
    try:
        for name, content in outputs.items():
            (staged / name).write_bytes(content)
        if os.path.lexists(output):
            raise FileExistsError("输出路径已存在，请指定新目录保留既有材料")
        _rename_with_retry(staged, output)
        staged = None
    finally:
        if staged is not None:
            shutil.rmtree(staged)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = generate(args.root, args.output)
    except (ValueError, OSError) as error:
        parser.exit(2, f"硬材料生成失败 {error}\n请核对公开JSON输入与新输出目录。\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "task_status": result["task_status"],
                "candidates": len(result["course_candidates"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
