"""Compare a baseline with one evidence-linked reform under resource limits."""

import math
from numbers import Real


def _number(value, name: str, upper: float = math.inf) -> float:
    """Return a finite nonnegative number no greater than upper; reject bool."""
    valid = (
        not isinstance(value, bool)
        and isinstance(value, Real)
        and math.isfinite(value)
        and 0 <= value <= upper
    )
    if not valid:
        if math.isfinite(upper):
            raise ValueError(f"{name} must be a finite number in [0, {upper}]")
        raise ValueError(f"{name} must be a finite nonnegative number")
    return float(value)


def _credits(values, name: str) -> dict:
    if not isinstance(values, dict):
        raise ValueError(f"{name} must be an object mapping module names to credits")
    for module, amount in values.items():
        if not isinstance(module, str) or not module.strip():
            raise ValueError(f"{name} has an empty module name; use nonempty strings")
        if type(amount) is not int or amount < 0:
            raise ValueError(f"{name}.{module} credits must be a nonnegative integer")
    return values


def _conservative_gain(lower: float, factors: list[float], bias: float) -> float:
    return min(factor * lower - bias for factor in factors)


def _select_plan(baseline_id: str, candidate: dict, gain: float) -> str:
    if candidate["feasible"] and gain > 1e-12:
        return candidate["plan_id"]
    return baseline_id


def compare_plans(config: dict, effect: dict) -> dict:
    """Use declared transfer scenarios and a bias budget, without combining reforms."""
    if not isinstance(config, dict):
        raise ValueError("plan configuration must be an object")
    for field in ["outcome_id", "action_id"]:
        if not isinstance(config.get(field), str) or not config[field].strip():
            raise ValueError(f"plan configuration requires {field}")
    total = config.get("total_credits")
    if type(total) is not int or total <= 0:
        raise ValueError("total_credits must be a positive integer")
    minimum = _credits(config.get("minimum_credits"), "minimum")
    maximum = _credits(config.get("maximum_credits"), "maximum")
    budget = _number(config.get("budget"), "budget")
    bias = _number(config.get("bias_budget"), "bias_budget", 1)
    factors = config.get("transfer_factors")
    if not isinstance(factors, list) or not factors:
        raise ValueError("transfer_factors must be a nonempty list")
    factors = [_number(value, "transfer_factor", 1) for value in factors]
    candidates = config.get("plans")
    if not isinstance(candidates, list) or len(candidates) != 2:
        raise ValueError("exactly one baseline and one reform candidate are supported")
    if not all(isinstance(plan, dict) for plan in candidates):
        raise ValueError("each plan must be an object")
    baseline = [plan for plan in candidates if plan.get("action_id") is None]
    if len(baseline) != 1:
        raise ValueError("exactly one baseline with action_id=null is required")
    modules = set(_credits(baseline[0].get("credits"), "baseline"))
    if not modules or not set(minimum).union(maximum).issubset(modules):
        raise ValueError("constraints must refer to existing modules")
    if any(minimum.get(key, 0) > maximum[key] for key in maximum):
        raise ValueError("minimum credits exceed maximum credits")
    # The estimator returns finite numbers with a ci95 interval around the estimate.
    estimate = effect["estimate"]
    lower, upper = effect["ci95"]
    records = []
    identifiers = set()
    for plan in candidates:
        identifier = plan.get("plan_id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in identifiers:
            raise ValueError("plan_id must be nonempty and unique")
        identifiers.add(identifier)
        credits = _credits(plan.get("credits"), identifier)
        if set(credits) != modules:
            raise ValueError("all plans must use identical module names")
        cost = _number(plan.get("cost"), "cost")
        is_baseline = plan.get("action_id") is None
        if not is_baseline and plan.get("action_id") != config["action_id"]:
            raise ValueError("candidate action_id must match evidence")
        if is_baseline and cost != 0:
            raise ValueError("baseline must have zero incremental cost")
        violations = []
        if sum(credits.values()) != total:
            violations.append("total_credits")
        if cost > budget:
            violations.append("budget")
        violations.extend(
            f"minimum:{key}" for key, value in minimum.items() if credits[key] < value
        )
        violations.extend(
            f"maximum:{key}" for key, value in maximum.items() if credits[key] > value
        )
        if is_baseline and violations:
            raise ValueError("baseline itself must be feasible")
        conservative = 0.0
        scenarios = []
        if not is_baseline:
            conservative = _conservative_gain(lower, factors, bias)
            scenarios = [
                {
                    "transfer_factor_assumption": factor,
                    "estimated_gain": factor * estimate,
                    "lower_gain_with_bias_budget": factor * lower - bias,
                }
                for factor in factors
            ]
        records.append(
            {
                "plan_id": identifier,
                "cost": cost,
                "credits": credits,
                "feasible": not violations,
                "violations": violations,
                "conservative_gain": conservative,
                "scenarios": scenarios,
            }
        )
    baseline_record = next(row for row in records if row["plan_id"] == baseline[0]["plan_id"])
    candidate = next(row for row in records if row is not baseline_record)
    sensitivity = []
    for factor in sorted({0.0, 0.25, 0.5, 0.75, 1.0, *factors}):
        for bias_assumption in sorted({0.0, 0.005, 0.01, 0.02, 0.04, bias}):
            gain = _conservative_gain(lower, [factor], bias_assumption)
            sensitivity.append(
                {
                    "transfer_factor_assumption": factor,
                    "bias_budget_assumption": bias_assumption,
                    "conservative_gain": gain,
                    "selected_plan": _select_plan(baseline_record["plan_id"], candidate, gain),
                }
            )
    return {
        "selected_plan": _select_plan(
            baseline_record["plan_id"], candidate, candidate["conservative_gain"]
        ),
        "plans": records,
        "bias_budget_assumption": bias,
        "selection_rule": "largest positive conservative gain, otherwise unchanged baseline",
        "baseline_plan_id": baseline_record["plan_id"],
        "constraints": {
            "total_credits": total,
            "minimum_credits": minimum,
            "maximum_credits": maximum,
            "budget": budget,
        },
        "credit_changes": [
            {
                "module": module,
                "baseline": baseline_record["credits"][module],
                "candidate": candidate["credits"][module],
                "delta": candidate["credits"][module] - baseline_record["credits"][module],
            }
            for module in sorted(modules)
        ],
        "sensitivity": sensitivity,
    }
