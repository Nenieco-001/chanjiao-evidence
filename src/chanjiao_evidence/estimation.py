"""Two-period DiD on unit changes, with explicit diagnostic comparisons."""

import numpy as np
import pandas as pd
import statsmodels.api as sm

from .dataset import validate_frame


def _estimate(frame: pd.DataFrame, before: int, after: int) -> dict:
    outcomes = frame.pivot(index="unit_id", columns="year", values="outcome").sort_index()
    treated = frame.groupby("unit_id").treated.first().reindex(outcomes.index)
    changes = outcomes[after] - outcomes[before]
    design = pd.DataFrame({"intercept": 1.0, "treated": treated}, index=outcomes.index)
    fitted = sm.OLS(changes, design).fit(cov_type="HC3", use_t=True)
    interval = fitted.conf_int(alpha=0.05).loc["treated"]
    values = [fitted.params["treated"], fitted.bse["treated"], *interval]
    if not np.isfinite(values).all():
        raise ValueError("estimator produced nonfinite values")
    treated_change = float(changes[treated == 1].mean())
    control_change = float(changes[treated == 0].mean())
    return {
        "before_year": before,
        "after_year": after,
        "estimate": float(fitted.params["treated"]),
        "standard_error": float(fitted.bse["treated"]),
        "ci95": [float(value) for value in interval],
        "treated_change": treated_change,
        "control_change": control_change,
        "treated_units": int(treated.sum()),
        "control_units": int((1 - treated).sum()),
        "method": "equal-unit change-score OLS, HC3 covariance, t interval",
    }


def analyze_panel(frame: pd.DataFrame, adoption_year: int) -> dict:
    """Estimate conditional effects. Diagnostics do not certify causality."""
    data = validate_frame(frame, adoption_year)
    main = _estimate(data, adoption_year - 1, adoption_year)
    leave_out = []
    for unit in sorted(data.unit_id.unique()):
        estimate = _estimate(data[data.unit_id != unit], adoption_year - 1, adoption_year)
        leave_out.append({"excluded_unit": unit, "estimate": estimate["estimate"]})
    return {
        "main": main,
        "placebo": _estimate(data, adoption_year - 2, adoption_year - 1),
        "leave_one_unit_out": leave_out,
        "bias_to_erase_point_estimate": abs(main["estimate"]),
        "interpretation": "ATT only conditional on design and identification assumptions",
        "assumptions": [
            "parallel untreated trends",
            "no anticipation or spillovers",
            "stable outcome definition and population composition",
            "independent units, common adoption date, equal unit weights",
        ],
    }
