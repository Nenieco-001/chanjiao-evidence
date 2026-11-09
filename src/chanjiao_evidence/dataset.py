"""Load a single-outcome, common-adoption, balanced school-level panel."""

import io
import json
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd


def validate_frame(frame: pd.DataFrame, adoption_year: int) -> pd.DataFrame:
    """Return normalized data or reject structures outside the supported design."""
    if type(adoption_year) is not int:
        raise ValueError(
            "adoption_year must be an integer; set metadata.adoption_year to a year such as 2022"
        )
    if sorted(frame.columns.tolist()) != ["outcome", "treated", "unit_id", "year"]:
        raise ValueError(
            "panel columns must be exactly unit_id, year, treated, outcome; "
            f"found {list(frame.columns)}"
        )
    data = frame.copy()
    if data.empty:
        raise ValueError("panel has no rows; provide the three-year records")
    missing = [column for column in data.columns if data[column].isna().any()]
    if missing:
        raise ValueError(f"panel has missing values in columns: {', '.join(missing)}")
    data["unit_id"] = data["unit_id"].astype(str).str.strip()
    if data.unit_id.eq("").any():
        raise ValueError("unit_id must be nonempty; fill the blank unit identifiers")
    for column in ["year", "treated", "outcome"]:
        try:
            data[column] = pd.to_numeric(data[column], errors="raise")
        except (TypeError, ValueError) as error:
            raise ValueError(f"{column} must be numeric; fix the invalid value ({error})") from None
        if not np.isfinite(data[column]).all():
            raise ValueError(f"{column} must contain finite numbers; replace inf or NaN")
    if not data.year.eq(data.year.round()).all():
        raise ValueError("year must be an integer; remove fractional years")
    data["year"] = data.year.astype(int)
    expected_years = {adoption_year - 2, adoption_year - 1, adoption_year}
    if set(data.year) != expected_years:
        found = ", ".join(str(year) for year in sorted(set(data.year)))
        raise ValueError(
            f"years must be {sorted(expected_years)} for adoption_year {adoption_year}; "
            f"found {found}"
        )
    if not data.treated.isin([0, 1]).all():
        raise ValueError("treated must be 0 or 1; mark every unit-year as treated=1 or control=0")
    data["treated"] = data.treated.astype(int)
    if not data.outcome.between(0, 1).all():
        raise ValueError("outcome must be a proportion between 0 and 1")
    if data.duplicated(["unit_id", "year"]).any():
        raise ValueError("panel repeats a unit-year record; drop or merge the duplicates")
    grouped = data.groupby("unit_id", sort=True)
    if not grouped.size().eq(3).all():
        raise ValueError("panel is unbalanced; each unit needs one row for each of the three years")
    if not grouped.treated.nunique().eq(1).all():
        raise ValueError("treated must stay fixed per unit; a unit cannot switch between groups")
    counts = grouped.treated.first().value_counts()
    if counts.get(0, 0) < 3 or counts.get(1, 0) < 3:
        raise ValueError("need at least three treated units and three control units")
    return data.sort_values(["unit_id", "year"]).reset_index(drop=True)


def validate_panel(frame: pd.DataFrame, metadata: dict) -> pd.DataFrame:
    """Validate metric definitions and provenance alongside the panel."""
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a JSON object")
    if type(metadata.get("schema_version")) is not int or metadata["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1; set metadata.schema_version to 1")
    if metadata.get("evidence_mode") not in {"synthetic", "historical"}:
        raise ValueError(
            "evidence_mode must be synthetic or historical; fix metadata.evidence_mode"
        )
    if metadata.get("outcome_unit") != "proportion":
        raise ValueError("outcome_unit must be proportion; fix metadata.outcome_unit")
    for field in ["outcome_id", "outcome_window", "population", "action_id", "data_license"]:
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            raise ValueError(f"metadata requires nonempty {field}; fill it in metadata.json")
    sources = metadata.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources must be a nonempty list; add at least one source object")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError(f"sources[{index}] must be a source object with title and url")
        for field in ["title", "url"]:
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise ValueError(f"sources[{index}].{field} must be a nonempty string")
        parsed = urlparse(source["url"])
        if metadata["evidence_mode"] == "historical" and (
            parsed.scheme != "https" or not parsed.netloc
        ):
            raise ValueError(f"sources[{index}].url must be an https URL for historical evidence")
    return validate_frame(frame, metadata.get("adoption_year"))


def parse_panel(csv_bytes: bytes, metadata_bytes: bytes) -> tuple[pd.DataFrame, dict]:
    """Parse and validate the exact bytes that are also hashed into the manifest."""
    metadata = json.loads(metadata_bytes.decode("utf-8"))
    frame = pd.read_csv(io.BytesIO(csv_bytes), dtype={"unit_id": str})
    return validate_panel(frame, metadata), metadata


def load_panel(csv_path: Path, metadata_path: Path) -> tuple[pd.DataFrame, dict]:
    """Read local files and validate them. Never fetch external data during a run."""
    return parse_panel(Path(csv_path).read_bytes(), Path(metadata_path).read_bytes())
