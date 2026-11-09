import copy

import pytest

from chanjiao_evidence.dataset import load_panel, validate_panel


def test_load_preserves_unit_identifiers(tmp_path, panel, metadata):
    import json

    panel["unit_id"] = panel["unit_id"].map(
        {f"{t}_{i}": f"0{t}{i}" for t in [0, 1] for i in range(3)}
    )
    panel.to_csv(tmp_path / "panel.csv", index=False)
    (tmp_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    loaded, details = load_panel(tmp_path / "panel.csv", tmp_path / "metadata.json")
    assert loaded.unit_id.iloc[0] == "000"
    assert details["evidence_mode"] == "synthetic"


@pytest.mark.parametrize(
    "corruption", ["duplicate", "missing", "group_change", "infinity", "range", "fractional_year"]
)
def test_reject_invalid_panel(panel, metadata, corruption):
    if corruption == "duplicate":
        panel.loc[len(panel)] = panel.iloc[0]
    elif corruption == "missing":
        panel = panel.drop(index=0)
    elif corruption == "group_change":
        panel.loc[0, "treated"] = 1
    elif corruption == "infinity":
        panel.loc[0, "outcome"] = float("inf")
    elif corruption == "range":
        panel.loc[0, "outcome"] = 1.1
    else:
        panel["year"] = panel["year"].astype(float)
        panel.loc[0, "year"] = 2020.5
    with pytest.raises(ValueError):
        validate_panel(panel, metadata)


@pytest.mark.parametrize(
    "key,value",
    [
        ("outcome_window", ""),
        ("evidence_mode", "realistic"),
        ("outcome_unit", "percent"),
        ("adoption_year", True),
    ],
)
def test_reject_ambiguous_metadata(panel, metadata, key, value):
    details = copy.deepcopy(metadata)
    details[key] = value
    with pytest.raises(ValueError):
        validate_panel(panel, details)


def test_historical_sources_require_public_urls(panel, metadata):
    metadata["evidence_mode"] = "historical"
    with pytest.raises(ValueError, match="https"):
        validate_panel(panel, metadata)
