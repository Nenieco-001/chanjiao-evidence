import pandas as pd
import pytest


@pytest.fixture
def panel():
    records = []
    for treated, changes in [(0, [0.01, 0.02, 0.03]), (1, [0.07, 0.08, 0.09])]:
        for index, change in enumerate(changes):
            before = 0.4 + index * 0.01
            for year, outcome in [(2020, before - 0.02), (2021, before), (2022, before + change)]:
                records.append(
                    dict(unit_id=f"{treated}_{index}", year=year, treated=treated, outcome=outcome)
                )
    return pd.DataFrame(records)


@pytest.fixture
def metadata():
    return {
        "schema_version": 1,
        "evidence_mode": "synthetic",
        "outcome_id": "employment_rate",
        "outcome_unit": "proportion",
        "outcome_window": "six months after graduation",
        "population": "synthetic university departments",
        "action_id": "supervised_internship",
        "adoption_year": 2022,
        "data_license": "MIT, generated fixture",
        "sources": [{"title": "generated fixture", "url": "synthetic://fixture"}],
    }


@pytest.fixture
def plans():
    return {
        "outcome_id": "employment_rate",
        "action_id": "supervised_internship",
        "total_credits": 30,
        "minimum_credits": {"foundation": 12},
        "maximum_credits": {"internship": 6},
        "budget": 10,
        "transfer_factors": [0.5, 1.0],
        "bias_budget": 0.01,
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
