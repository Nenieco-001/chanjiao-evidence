"""Reproducible local pipeline with exclusive, complete artifact publication."""

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import tempfile
from pathlib import Path

from . import __version__
from .dataset import load_panel
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
    """Validate inputs and atomically publish a new report directory."""
    destination = Path(output_dir).absolute()
    if os.path.lexists(destination):
        raise FileExistsError(f"output already exists: {destination}")
    paths = {"panel": Path(panel_path), "metadata": Path(metadata_path), "plans": Path(plans_path)}
    input_content = {role: path.read_bytes() for role, path in paths.items()}
    frame, metadata = load_panel(paths["panel"], paths["metadata"])
    plans = json.loads(input_content["plans"])
    for field in ["outcome_id", "action_id"]:
        if plans.get(field) != metadata[field]:
            raise ValueError(f"plan {field} does not match panel metadata")
    analysis = analyze_panel(frame, metadata["adoption_year"])
    planning = compare_plans(plans, analysis["main"])
    # Fail if an input changed while it was being loaded, rather than hashing a different dataset.
    if any(path.read_bytes() != input_content[role] for role, path in paths.items()):
        raise ValueError("input changed during execution")
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
    lock_path = destination.with_name(f".{destination.name}.lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    staging = None
    try:
        os.close(lock_fd)
        if os.path.lexists(destination):
            raise FileExistsError(f"output already exists: {destination}")
        staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
        (staging / "report.json").write_bytes(report_bytes)
        (staging / "manifest.json").write_bytes(_json_bytes(manifest))
        if os.path.lexists(destination):
            raise FileExistsError(f"output already exists: {destination}")
        os.rename(staging, destination)
        staging = None
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        lock_path.unlink()
    return report
