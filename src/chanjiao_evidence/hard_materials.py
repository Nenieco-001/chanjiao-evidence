"""Recompute curriculum actions and publish explicit evidence for the four tasks."""

import copy
import math

from .comparison import compare_supply_demand
from .curriculum import _finite_sum, _number, _text
from .scenarios import evaluate_scenarios
from .strategy import evaluate_strategy


def _net_change(changes, field):
    if any(row[field + suffix] is None for row in changes for suffix in ("_before", "_after")):
        return None
    return _finite_sum((row[field + "_after"] - row[field + "_before"] for row in changes), field)


def _validate_actions(actions, catalog, program, policy, comparison):
    if (
        not isinstance(actions, dict)
        or type(actions.get("schema_version")) is not int
        or actions["schema_version"] != 1
        or actions.get("evidence_mode") != "scenario_assumptions"
    ):
        raise ValueError("actions 格式无效，请提供schema_version=1的scenario_assumptions对象")
    merges = actions.get("merges")
    if not isinstance(merges, list):
        raise ValueError("actions.merges 无效，请填写合并情景列表")
    seen = {row["scenario_id"] for row in policy["curriculum_scenarios"]} | {
        "unchanged",
        "directions",
        "admissions",
    }
    for merge in merges:
        if not isinstance(merge, dict):
            raise ValueError("actions.merges 项无效，请填写对象")
        identifier = merge.get("candidate_id")
        _text(identifier, "actions.merges.candidate_id")
        if identifier in seen:
            raise ValueError("actions.merges.candidate_id 重复，请使用唯一情景标识")
        seen.add(identifier)
        sources = merge.get("source_course_ids")
        if (
            not isinstance(sources, list)
            or len(sources) < 2
            or any(not isinstance(value, str) or value not in catalog for value in sources)
            or len(set(sources)) != len(sources)
        ):
            raise ValueError("actions.merges.source_course_ids 无效，请选两门以上不同的公开课程ID")
        target = merge.get("proposed_course")
        if not isinstance(target, dict):
            raise ValueError("actions.merges.proposed_course 缺失，请提供拟设课程对象")
        for field in ("course_id", "title", "module_id"):
            _text(target.get(field), "actions.merges.proposed_course." + field)
        if (
            target["course_id"] in catalog
            or target["module_id"] not in program["module_minimum_credits"]
        ):
            raise ValueError("actions.merges.proposed_course 标识冲突或模块未知，请核对目录与模块")
        for field in ("credits", "hours"):
            _number(target.get(field), "actions.merges.proposed_course." + field)
        semesters = target.get("semesters")
        if (
            not isinstance(semesters, list)
            or not semesters
            or any(type(value) is not int or value <= 0 for value in semesters)
        ):
            raise ValueError("actions.merges.proposed_course.semesters 无效，请填写正整数学期列表")
        notes = merge.get("assumptions")
        if not isinstance(notes, list) or not notes:
            raise ValueError("actions.merges.assumptions 缺失，请登记拟设课程与资源假设")
        for note in notes:
            _text(note, "actions.merges.assumptions")
        for source in sources:
            if catalog[source]["module_id"] != program["course_modules"][source]:
                raise ValueError("actions.source 模块与课程映射冲突，请核对同版目录")
            for field in ("credits", "hours"):
                if catalog[source][field] is not None:
                    _number(catalog[source][field], f"actions.source.{source}.{field}")
    carriers = actions.get("planned_skill_carriers")
    if not isinstance(carriers, list):
        raise ValueError("actions.planned_skill_carriers 无效，请填写拟定内容承载课程")
    covered = set()
    for row in carriers:
        if (
            not isinstance(row, dict)
            or row.get("course_id") not in catalog
            or row.get("skill") not in comparison["planned_skills"]
        ):
            raise ValueError("actions.planned_skill_carriers 引用无效，请核对课程ID与拟定技能")
        _text(row.get("proposal"), "actions.planned_skill_carriers.proposal")
        key = (row["skill"], row["course_id"])
        if key in covered:
            raise ValueError("actions.planned_skill_carriers 重复，请保留唯一关系")
        covered.add(key)
    if {skill for skill, _ in covered} != set(comparison["planned_skills"]):
        raise ValueError("actions.planned_skill_carriers 缺项，请逐项登记拟定技能")
    controls = actions.get("risk_controls")
    if not isinstance(controls, dict) or set(controls) != {
        row["risk_id"] for row in policy["risks"]
    }:
        raise ValueError("actions.risk_controls 缺项，请逐项绑定政策风险ID")
    for control in controls.values():
        if not isinstance(control, dict):
            raise ValueError("actions.risk_controls 项无效，请填写对象")
        for field in ("timing", "indicator", "threshold", "response"):
            _text(control.get(field), "actions.risk_controls." + field)


def _merge_candidate(merge, catalog, program, paths):
    sources = [catalog[key] for key in merge["source_course_ids"]]
    target = merge["proposed_course"]
    changes = [
        {
            "course_id": course["course_id"],
            "title": course["title"],
            "module_id": course["module_id"],
            "action_type": "delete",
            "hours_before": course["hours"],
            "hours_after": 0,
            "credits_before": course["credits"],
            "credits_after": 0,
            "source_location": course["source_location"],
            "evidence_kind": "scenario_assumptions",
        }
        for course in sources
    ]
    changes.append(
        {
            "course_id": target["course_id"],
            "title": target["title"],
            "module_id": target["module_id"],
            "action_type": "add",
            "hours_before": 0,
            "hours_after": target["hours"],
            "credits_before": 0,
            "credits_after": target["credits"],
            "source_location": "拟合并原课程，来源为删除行所列公开课程位置",
            "evidence_kind": "scenario_assumptions",
        }
    )
    missing = [
        f"{course['course_id']}.{field}"
        for course in sources
        for field in ("credits", "hours")
        if course[field] is None
    ]
    result = {
        "candidate_id": merge["candidate_id"],
        "scenario_id": merge["candidate_id"],
        "kind": "merge",
        "status": "not_evaluable",
        "approval_status": "pending_school_review",
        "course_changes": changes,
        "student_paths": [],
        "missing_inputs": missing,
        "violations": [],
        "net_credit_delta": None,
        "net_hour_delta": None,
        "assumptions": list(merge["assumptions"]),
        "semesters": list(target["semesters"]),
        "unverified_constraints": [
            "course_objective_equivalence",
            "prerequisites",
            "semester_workload",
            "teaching_resources",
            "school_course_registration",
        ],
    }
    if missing:
        return result
    for field, name in [("credits", "net_credit_delta"), ("hours", "net_hour_delta")]:
        result[name] = _finite_sum(
            [target[field], *(-course[field] for course in sources)], "actions." + name
        )
        if not math.isclose(result[name], 0, rel_tol=0, abs_tol=1e-9):
            result["violations"].append(field + "_conservation")
    for path in paths:
        deltas = {module: [credits] for module, credits in path["module_credits"].items()}
        for course in sources:
            deltas[course["module_id"]].append(-course["credits"])
        deltas[target["module_id"]].append(target["credits"])
        after = {
            module: _finite_sum(values, "actions.module_credits_after." + module)
            for module, values in deltas.items()
        }
        violations = list(result["violations"])
        violations += [
            "source_not_selected:" + course["course_id"]
            for course in sources
            if course["course_id"] not in path["selected_course_ids"]
        ]
        violations += [
            "module_minimum:" + module
            for module, minimum in program["module_minimum_credits"].items()
            if after[module] < minimum
        ]
        total = _finite_sum(after.values(), "actions.total_credits_after")
        if total < program["minimum_total_credits"]:
            violations.append("minimum_total_credits")
        result["student_paths"].append(
            {
                "path_id": path["path_id"],
                "status": "invalid" if violations else "valid",
                "violations": violations,
                "module_credits_before": dict(path["module_credits"]),
                "module_credits_after": after,
                "total_credits_after": total,
            }
        )
    result["status"] = (
        "invalid"
        if result["violations"] or any(row["violations"] for row in result["student_paths"])
        else "valid"
    )
    return result


def evaluate_hard_materials(
    *, plan, program, policy, demand, comparison, evidence, effects, actions
):
    """Evaluate the existing strategy and proposed course mergers on the same paths."""
    strategy = evaluate_strategy(plan, policy, program)
    supply_demand = compare_supply_demand(program, demand, comparison)
    effect_result = evaluate_scenarios(evidence, effects)
    catalog = {row["course_id"]: row for row in program["courses"]}
    for course in plan["courses"]:
        published = catalog.get(course["course_id"])
        if published is None or any(
            course[field] is not None
            and published[field] is not None
            and course[field] != published[field]
            for field in ("title", "credits", "hours", "semester")
        ):
            raise ValueError("课程事实不一致，请核对切片与同版专业目录的名称、学分、学时及学期")
    _validate_actions(actions, catalog, program, policy, comparison)
    candidates = []
    for scenario in strategy["scenario_results"]:
        for candidate in scenario["candidates"]:
            if candidate["kind"] == "baseline" and candidates:
                continue
            changes = [
                {
                    **row,
                    "module_id": program["course_modules"][row["course_id"]],
                    "action_type": "retain" if candidate["kind"] == "baseline" else "adjust_hours",
                    "evidence_kind": "published_curriculum"
                    if candidate["kind"] == "baseline"
                    else "scenario_assumptions",
                }
                for row in candidate["course_changes"]
            ]
            candidates.append(
                {
                    "candidate_id": "unchanged"
                    if candidate["kind"] == "baseline"
                    else scenario["scenario_id"] + "/" + candidate["candidate_id"],
                    "scenario_id": scenario["scenario_id"],
                    "kind": candidate["kind"],
                    "status": candidate["status"],
                    "added_hours": candidate["added_hours"],
                    "net_credit_delta": _net_change(changes, "credits"),
                    "net_hour_delta": _net_change(changes, "hours"),
                    "approval_status": "pending_school_review",
                    "course_changes": changes,
                    "student_paths": copy.deepcopy(candidate["student_paths"]),
                    "violations": list(candidate["violations"]),
                    "missing_inputs": list(candidate["missing_inputs"]),
                    "unverified_constraints": list(scenario["unverified_constraints"]),
                }
            )
    candidates += [
        _merge_candidate(merge, catalog, program, policy["student_paths"])
        for merge in actions["merges"]
    ]
    carriers = []
    for link in comparison["skill_links"]:
        course = catalog[link["course_id"]]
        carriers.append(
            {
                **link,
                "title": course["title"],
                "scenario_id": "unchanged",
                "evidence_kind": "course_name",
                "requirement": course["requirement"],
            }
        )
    for link in actions["planned_skill_carriers"]:
        course = catalog[link["course_id"]]
        carriers.append(
            {
                **link,
                "title": course["title"],
                "scenario_id": "within_core",
                "source_location": course["source_location"],
                "evidence_kind": "proposed_content",
                "requirement": course["requirement"],
            }
        )
        for merge in actions["merges"]:
            replacement = (
                merge["proposed_course"]
                if course["course_id"] in merge["source_course_ids"]
                else course
            )
            carriers.append(
                {
                    **link,
                    "course_id": replacement["course_id"],
                    "title": replacement["title"],
                    "scenario_id": merge["candidate_id"],
                    "source_location": course["source_location"],
                    "evidence_kind": "proposed_content",
                    "requirement": "pending_review",
                }
            )
    risks = []
    for row in strategy["risk_matrix"]:
        related = [row["action_id"]]
        if row["action_id"] == "within_core":
            related.extend(merge["candidate_id"] for merge in actions["merges"])
        risks.append(
            {
                **row,
                **actions["risk_controls"][row["risk_id"]],
                "probability_status": "unknown"
                if row["probability_range"] == [0, 1]
                else "assumed_range",
                "empirical_probability": None,
                "related_scenarios": related,
            }
        )
    supply_demand["skills"]["measure_label"] = "课程名称级匹配下界"
    path_name_bounds = []
    for path in policy["student_paths"]:
        skills = {
            row["skill"]
            for row in comparison["skill_links"]
            if row["course_id"] in path["selected_course_ids"]
        }
        weight = _finite_sum(
            (demand["skill_counts"][skill] for skill in skills), "path_name_match_weight"
        )
        denominator = supply_demand["skills"]["mention_denominator"]
        path_name_bounds.append(
            {
                "path_id": path["path_id"],
                "matched_skills": sorted(skills),
                "matched_weight": weight,
                "mention_denominator": denominator,
                "lower_bound": weight / denominator if denominator else None,
                "evidence_mode": "scenario_assumptions",
            }
        )
    return {
        "schema_version": 1,
        "evidence_mode": "scenario_assumptions",
        "selected_candidate_id": "unchanged",
        "school": program["school"],
        "major": program["major"],
        "program_version": program["program_version"],
        "minimum_total_credits": program["minimum_total_credits"],
        "module_minimum_credits": copy.deepcopy(program["module_minimum_credits"]),
        "course_candidates": candidates,
        "skill_carriers": carriers,
        "path_name_match_lower_bounds": path_name_bounds,
        "supply_demand": supply_demand,
        "effects": effect_result,
        "direction_policy": strategy["direction_policy"],
        "admissions": strategy["admissions"],
        "risks": risks,
        "process_log": strategy["process_log"],
        "task_status": {"T1": "PARTIAL", "T2": "PARTIAL", "T3": "PASS", "T4": "PASS"},
        "unknowns": strategy["unknowns"],
    }
