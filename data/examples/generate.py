"""Regenerate public synthetic fixtures. All values and true effects are declared."""

import argparse
import csv
import json
from pathlib import Path


def generate(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name, effect in [("panel", 0.04), ("null_panel", 0.0)]:
        with (destination / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["unit_id", "year", "treated", "outcome"])
            for treated in [0, 1]:
                for index in range(8):
                    base = 0.45 + 0.01 * index + 0.015 * treated
                    local_trend = 0.02 + ((index % 4) - 1.5) * 0.003
                    for time, year in enumerate([2020, 2021, 2022]):
                        outcome = base + time * local_trend
                        if time == 2:
                            outcome += treated * effect
                        writer.writerow(
                            [f"synthetic_{treated}_{index:02d}", year, treated, f"{outcome:.6f}"]
                        )
        metadata = {
            "schema_version": 1,
            "evidence_mode": "synthetic",
            "outcome_id": "employment_rate",
            "outcome_unit": "proportion",
            "outcome_window": "six months after graduation",
            "population": "16 synthetic departments, 8 per group; no real students",
            "action_id": "supervised_internship",
            "adoption_year": 2022,
            "data_license": "MIT, original synthetic data",
            "sources": [{"title": "data/examples/generate.py", "url": "synthetic://generator/v1"}],
            "known_synthetic_effect": effect,
            "generation": (
                "Fixed group levels and shared trend distribution, with additive reform effect."
            ),
        }
        metadata_name = "metadata.json" if name == "panel" else "null_metadata.json"
        (destination / metadata_name).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    plans = {
        "outcome_id": "employment_rate",
        "action_id": "supervised_internship",
        "total_credits": 30,
        "minimum_credits": {"foundation": 12},
        "maximum_credits": {"internship": 6},
        "budget": 10,
        "transfer_factors": [0.5, 0.75, 1.0],
        "bias_budget": 0.01,
        "assumption_notes": (
            "Credits, costs, transfer factors and bias budget are synthetic assumptions."
        ),
        "plans": [
            {
                "plan_id": "unchanged",
                "action_id": None,
                "cost": 0,
                "credits": {"foundation": 14, "specialty": 14, "internship": 2},
            },
            {
                "plan_id": "internship",
                "action_id": "supervised_internship",
                "cost": 8,
                "credits": {"foundation": 14, "specialty": 10, "internship": 6},
            },
        ],
    }
    (destination / "plans.json").write_text(json.dumps(plans, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    generate(parser.parse_args().output)
