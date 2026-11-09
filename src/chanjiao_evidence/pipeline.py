"""Reproducible local pipeline: compute fully, then publish one new artifact directory."""

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import tempfile
import time
from pathlib import Path

from . import __version__
from .dataset import parse_panel
from .estimation import analyze_panel
from .evidence import parse_evidence
from .planning import compare_plans
from .reporting import render_html, render_markdown

LIMITATIONS = [
    "因果解释依赖平行趋势、无提前反应、无干扰和口径稳定，需要改革材料与同期对照支持。",
    "改革前只有两个年份，伪改革接近零仍缺更长趋势记录；HC3 区间仅表示近似抽样不确定性。",
    "当前结果是学校或专业就业比例，学生工作能力需要另行取得任务表现数据。",
    "迁移系数和偏差预算由方案输入指定；确定真实取值需要相近学校的外部回测。",
    "当前只比较一项改革；专业课被替代的损失及改革组合交互需要单独测量。",
    "文献卡片仅供查阅，真实改革面板、适用人群和结果口径仍须逐项核对。",
]


def _json_bytes(value: dict) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


_RENAME_ATTEMPTS = 5


def _rename_with_retry(source: Path, destination: Path) -> None:
    """Publish with a bounded retry for transient Windows locks on the new files.

    Windows antivirus and search indexers can briefly hold a directory after its
    files are written. Only sharing/lock violations (winerror 5 or 32) are retried;
    a real permission problem or an existing destination still fails immediately.
    """
    for attempt in range(1, _RENAME_ATTEMPTS + 1):
        try:
            os.rename(source, destination)
            return
        except PermissionError as error:
            if getattr(error, "winerror", None) not in {5, 32} or attempt == _RENAME_ATTEMPTS:
                raise
            time.sleep(0.05 * attempt)


def run(
    panel_path: Path,
    metadata_path: Path,
    plans_path: Path,
    output_dir: Path,
    *,
    evidence_path: Path | None = None,
) -> dict:
    """Validate inputs and atomically publish a new report directory.

    Single writer: two runs must not target the same output path, so this
    function does not lock; a race still fails instead of overwriting.
    """
    destination = Path(output_dir).absolute()
    if os.path.lexists(destination):
        raise FileExistsError(
            f"output already exists: {destination}; choose a new output directory"
        )
    paths = {"panel": Path(panel_path), "metadata": Path(metadata_path), "plans": Path(plans_path)}
    if evidence_path is not None:
        paths["evidence"] = Path(evidence_path)
    input_content = {role: path.read_bytes() for role, path in paths.items()}
    # Parse the same bytes that are hashed below, so report and manifest cannot diverge.
    frame, metadata = parse_panel(input_content["panel"], input_content["metadata"])
    plans = json.loads(input_content["plans"])
    if not isinstance(plans, dict):
        raise ValueError("plans JSON must be an object with outcome_id, action_id and plans")
    for field in ["outcome_id", "action_id"]:
        if plans.get(field) != metadata[field]:
            raise ValueError(f"plan {field} does not match panel metadata")
    analysis = analyze_panel(frame, metadata["adoption_year"])
    planning = compare_plans(plans, analysis["main"])
    evidence = parse_evidence(input_content.get("evidence"), metadata["outcome_id"])
    means = frame.groupby(["year", "treated"]).outcome.mean().unstack("treated")
    limitations = list(LIMITATIONS)
    if metadata["evidence_mode"] == "synthetic":
        limitations.insert(0, "当前面板全部为合成数据，所得效应只检验实现，不解释真实学校。")
    report = {
        "schema_version": 1,
        "metadata": metadata,
        "analysis": analysis,
        "planning": planning,
        "limitations": limitations,
        "trajectory": [
            {"year": int(year), "treated_mean": float(row[1]), "control_mean": float(row[0])}
            for year, row in means.iterrows()
        ],
        "evidence": evidence,
    }
    outputs = {
        "report.json": _json_bytes(report),
        "report.html": render_html(report).encode("utf-8"),
        "report.md": render_markdown(report).encode("utf-8"),
    }
    source = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(Path(__file__).parent.glob("*.py"))
    }
    manifest = {
        "schema_version": 1,
        "package_version": __version__,
        "python": platform.python_version(),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ["statsmodels", "pandas", "numpy", "scipy"]
        },
        "inputs": {
            role: hashlib.sha256(content).hexdigest() for role, content in input_content.items()
        },
        "source_sha256": source,
        "outputs": {name: hashlib.sha256(content).hexdigest() for name, content in outputs.items()},
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        for name, content in outputs.items():
            (staging / name).write_bytes(content)
        (staging / "manifest.json").write_bytes(_json_bytes(manifest))
        if os.path.lexists(destination):
            raise FileExistsError(
                f"output already exists: {destination}; choose a new output directory"
            )
        _rename_with_retry(staging, destination)
        staging = None
    finally:
        if staging is not None:
            shutil.rmtree(staging)
    return report
