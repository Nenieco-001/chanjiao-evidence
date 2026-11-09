"""Reproducible local pipeline: compute fully, then publish one new artifact directory."""

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import tempfile
from pathlib import Path

from . import __version__
from .dataset import parse_panel
from .estimation import analyze_panel
from .planning import compare_plans

LIMITATIONS = [
    "Synthetic data only validate implementation, not real reform effectiveness.",
    "Causal interpretation requires parallel trends and the other stated assumptions.",
    "A short placebo period cannot establish parallel trends. HC3 intervals are approximate.",
    "School-level employment effects do not establish individual skill improvement.",
    "Transfer factors and bias budgets are sensitivity assumptions requiring external support.",
    "One reform comparison excludes interactions and unmeasured displaced-course losses.",
]


def _json_bytes(value: dict) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def run(panel_path: Path, metadata_path: Path, plans_path: Path, output_dir: Path) -> dict:
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
    report = {
        "schema_version": 1,
        "metadata": metadata,
        "analysis": analysis,
        "planning": planning,
        "limitations": LIMITATIONS,
    }
    report_bytes = _json_bytes(report)
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
        "outputs": {"report.json": hashlib.sha256(report_bytes).hexdigest()},
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    try:
        (staging / "report.json").write_bytes(report_bytes)
        (staging / "manifest.json").write_bytes(_json_bytes(manifest))
        if os.path.lexists(destination):
            raise FileExistsError(
                f"output already exists: {destination}; choose a new output directory"
            )
        os.rename(staging, destination)
        staging = None
    finally:
        if staging is not None:
            shutil.rmtree(staging)
    return report
