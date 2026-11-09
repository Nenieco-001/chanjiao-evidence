"""Load a single-outcome, common-adoption, balanced school-level panel."""

import json
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd


def validate_frame(frame: pd.DataFrame, adoption_year: int) -> pd.DataFrame:
    """Return normalized data or reject structures outside the supported design."""
    if type(adoption_year) is not int:
        raise ValueError("adoption_year must be an integer")
    if set(frame.columns) != {"unit_id", "year", "treated", "outcome"} or len(frame.columns) != 4:
        raise ValueError("panel must contain exactly unit_id, year, treated, outcome")
    data = frame.copy()
    if data.empty or data.isna().any().any():
        raise ValueError("panel must be nonempty with no missing values")
    data["unit_id"] = data["unit_id"].astype(str).str.strip()
    if data.unit_id.eq("").any():
        raise ValueError("unit_id must be nonempty")
    for column in ["year", "treated", "outcome"]:
        data[column] = pd.to_numeric(data[column], errors="raise")
        if not np.isfinite(data[column]).all():
            raise ValueError(f"{column} must contain finite numbers")
    if not data.year.eq(data.year.round()).all():
        raise ValueError("year must be integral")
    data["year"] = data.year.astype(int)
    if set(data.year) != {adoption_year - 2, adoption_year - 1, adoption_year}:
        raise ValueError("expected exactly two pre-reform years and the common adoption year")
    if not data.treated.isin([0, 1]).all():
        raise ValueError("treated must be 0 or 1")
    data["treated"] = data.treated.astype(int)
    if not data.outcome.between(0, 1).all():
        raise ValueError("outcome must be a proportion in [0, 1]")
    if data.duplicated(["unit_id", "year"]).any():
        raise ValueError("duplicate unit-year record")
    grouped = data.groupby("unit_id", sort=True)
    if not grouped.size().eq(3).all():
        raise ValueError("unbalanced panel")
    if not grouped.treated.nunique().eq(1).all():
        raise ValueError("treated group must be fixed across years")
    counts = grouped.treated.first().value_counts()
    if counts.get(0, 0) < 3 or counts.get(1, 0) < 3:
        raise ValueError("need at least three independent units per group")
    return data.sort_values(["unit_id", "year"]).reset_index(drop=True)


def validate_panel(frame: pd.DataFrame, metadata: dict) -> pd.DataFrame:
    """Validate metric definitions and provenance alongside the panel."""
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")
    if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    if metadata.get("evidence_mode") not in {"synthetic", "historical"}:
        raise ValueError("evidence_mode must be synthetic or historical")
    if metadata.get("outcome_unit") != "proportion":
        raise ValueError("outcome_unit must be proportion")
    for field in ["outcome_id", "outcome_window", "population", "action_id", "data_license"]:
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            raise ValueError(f"metadata requires nonempty {field}")
    sources = metadata.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources must be a nonempty list")
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("each source must be an object")
        for field in ["title", "url"]:
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise ValueError(f"source requires nonempty {field}")
        parsed = urlparse(source["url"])
        if metadata["evidence_mode"] == "historical" and (
            parsed.scheme != "https" or not parsed.netloc
        ):
            raise ValueError("historical sources require https URLs")
    return validate_frame(frame, metadata.get("adoption_year"))


def load_panel(csv_path: Path, metadata_path: Path) -> tuple[pd.DataFrame, dict]:
    """Read local inputs. Never fetch external data during a run."""
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    frame = pd.read_csv(csv_path, dtype={"unit_id": str})
    return validate_panel(frame, metadata), metadata
