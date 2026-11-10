"""Evaluate a published curriculum slice against declared reallocation scenarios."""

import copy
import math
import re
from numbers import Real
from urllib.parse import urlsplit


def _text(value, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} 缺少文字，请填写非空字符串")


def _number(value, field: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{field} 数值无效，请填写有限非负数")


def _validate_inputs(plan: dict, config: dict) -> dict:
    """Validate the two external JSON objects once, before generating candidates."""
    for name, value, mode in [
        ("plan", plan, "published_curriculum"),
        ("config", config, "scenario_assumptions"),
    ]:
        if not isinstance(value, dict):
            raise ValueError(f"{name} 格式无效，请提供 JSON 对象")
        if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
            raise ValueError(f"{name}.schema_version 无效，请填写整数 1")
        if value.get("evidence_mode") != mode:
            raise ValueError(f"{name}.evidence_mode 无效，请填写 {mode}")
    for field in ["school", "major", "program_version"]:
        _text(plan.get(field), field)
    if plan.get("coverage") != "selected_courses":
        raise ValueError("coverage 无效，请用 selected_courses 标明课程切片")
    source = plan.get("source")
    if not isinstance(source, dict):
        raise ValueError("source 缺少原文依据，请填写来源对象")
    for field in ["title", "url", "sha256", "location"]:
        _text(source.get(field), f"source.{field}")
    address = urlsplit(source["url"])
    if address.scheme != "https" or not address.hostname:
        raise ValueError("source.url 不是公开来源链接，请填写 https 原文地址")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", source["sha256"]):
        raise ValueError("source.sha256 无效，请填写原文件的 64 位十六进制哈希")
    courses = plan.get("courses")
    if not isinstance(courses, list) or not courses:
        raise ValueError("courses 为空或格式无效，请提供至少一门有来源的课程")
    course_map = {}
    for course in courses:
        if not isinstance(course, dict):
            raise ValueError("courses 项格式无效，请填写课程对象")
        for field in ["course_id", "title", "source_location"]:
            _text(course.get(field), f"courses.{field}")
        identifier = course["course_id"]
        if identifier in course_map:
            raise ValueError(f"course_id 重复 {identifier}，请保留每门课程的一条记录")
        for field in ["hours", "credits", "semester"]:
            if field not in course:
                raise ValueError(f"courses.{identifier}.{field} 缺失，未公开时请填写 null")
            value = course[field]
            if value is not None:
                _number(value, f"courses.{identifier}.{field}")
                if field == "semester" and (type(value) is not int or value == 0):
                    raise ValueError(f"courses.{identifier}.semester 无效，请填正整数或 null")
        prerequisites = course.get("prerequisites")
        if not isinstance(prerequisites, list):
            raise ValueError(f"courses.{identifier}.prerequisites 无效，请填课程 ID 列表")
        for prerequisite in prerequisites:
            _text(prerequisite, f"courses.{identifier}.prerequisites")
        course_map[identifier] = course
    for field in ["label", "rationale", "target_course_id", "donor_course_id"]:
        _text(config.get(field), field)
    for field in ["target_course_id", "donor_course_id"]:
        if config[field] not in course_map:
            raise ValueError(f"{field} 未在课程切片中找到，请填写已有 course_id")
    if config["target_course_id"] == config["donor_course_id"]:
        raise ValueError("donor_course_id 与 target_course_id 相同，请指定两门不同课程")
    options = config.get("hour_options")
    if not isinstance(options, list) or not options:
        raise ValueError("hour_options 无效，请填写至少一个非负课时增量")
    for value in options:
        _number(value, "hour_options")
    for field in ["credit_delta", "capacity_added_hours"]:
        _number(config.get(field), field)
    for field in ["minimum_hours", "minimum_credits"]:
        limits = config.get(field)
        if not isinstance(limits, dict):
            raise ValueError(f"{field} 无效，请填写课程 ID 到底线数值的对象")
        for identifier, value in limits.items():
            if identifier not in course_map:
                raise ValueError(f"{field}.{identifier} 不在课程切片中，请修改课程 ID")
            _number(value, f"{field}.{identifier}")
    notes = config.get("assumption_notes")
    if not isinstance(notes, list):
        raise ValueError("assumption_notes 无效，请填写情景假设的文字列表")
    for note in notes:
        _text(note, "assumption_notes")
    return course_map


def _constraint_gaps(courses: dict, config: dict) -> list[str]:
    gaps = ["unmodeled_program_credit_structure", "unmeasured_teaching_quality_and_staffing"]
    for identifier, course in courses.items():
        if course["semester"] is None:
            gaps.append(f"semester_not_published:{identifier}")
        if course.get("prerequisites_status") == "not_published":
            gaps.append(f"prerequisites_not_published:{identifier}")
        for prerequisite in course["prerequisites"]:
            if prerequisite not in courses:
                gaps.append(f"prerequisite_not_modeled:{prerequisite}->{identifier}")
        for field in ["minimum_hours", "minimum_credits"]:
            if identifier not in config[field]:
                gaps.append(f"{field}_not_specified:{identifier}")
    return gaps


def _evaluate_candidate(
    courses: dict, config: dict, identifier: str, hours: Real, credits: Real
) -> dict:
    target = config["target_course_id"]
    donor = config["donor_course_id"]
    changes = []
    after = {
        key: {field: row[field] for field in ["hours", "credits"]} for key, row in courses.items()
    }
    for course_id, sign in [(donor, -1), (target, 1)]:
        course = courses[course_id]
        change = {
            "course_id": course_id,
            "title": course["title"],
            "source_location": course["source_location"],
            "reason": "保持原方案，等待培养结果证据"
            if identifier == "unchanged"
            else config["rationale"],
        }
        for field, delta in [("hours", hours), ("credits", credits)]:
            before = course[field]
            after[course_id][field] = None if before is None else before + sign * delta
            change[f"{field}_before"] = before
            change[f"{field}_after"] = after[course_id][field]
        changes.append(change)
    missing = []
    violations = []
    totals = {}
    for field in ["hours", "credits"]:
        field_missing = [
            f"courses.{key}.{field}" for key, row in courses.items() if row[field] is None
        ]
        missing.extend(field_missing)
        totals[f"{field}_before"] = None
        totals[f"{field}_after"] = None
        if not field_missing:
            totals[f"{field}_before"] = math.fsum(row[field] for row in courses.values())
            totals[f"{field}_after"] = math.fsum(row[field] for row in after.values())
            if not math.isclose(totals[f"{field}_before"], totals[f"{field}_after"], abs_tol=1e-9):
                violations.append(f"total_{field}")
        for course_id, row in after.items():
            value = row[field]
            if value is not None and value < 0:
                violations.append(f"nonnegative_{field}:{course_id}")
            minimum = config[f"minimum_{field}"].get(course_id)
            if value is not None and minimum is not None and value < minimum:
                violations.append(f"minimum_{field}:{course_id}")
    if hours > config["capacity_added_hours"]:
        violations.append("capacity_added_hours")
    for course_id, course in courses.items():
        semester = course["semester"]
        for prerequisite_id in course["prerequisites"]:
            prerequisite = courses.get(prerequisite_id)
            if (
                prerequisite is not None
                and semester is not None
                and prerequisite["semester"] is not None
                and prerequisite["semester"] >= semester
            ):
                violations.append(f"prerequisite_order:{prerequisite_id}->{course_id}")
    status = "not_evaluable" if missing else "infeasible" if violations else "feasible"
    return {
        "candidate_id": identifier,
        "kind": "baseline" if identifier == "unchanged" else "transfer",
        "added_hours": hours,
        "credit_delta": credits,
        "status": status,
        "evaluable": not missing,
        "feasible": None if missing else not violations,
        "violations": violations,
        "missing_inputs": missing,
        "course_changes": changes,
        "totals": totals,
        "practice_input_proxy": {
            "course_id": target,
            "measure": "target_course_added_teaching_hours",
            "added_hours": hours,
            "interpretation": "只记录目标课程排定课时，实践占比和教学质量需另行核对",
            "student_mastery_effect": "unidentified",
        },
    }


def evaluate_curriculum(plan: dict, config: dict) -> dict:
    """Retain baseline and finite transfers, with no assumed student-outcome gain."""
    courses = _validate_inputs(plan, config)
    gaps = _constraint_gaps(courses, config)
    candidates = [_evaluate_candidate(courses, config, "unchanged", 0, 0)]
    options = sorted({hours for hours in config["hour_options"] if hours > 0})
    for index, hours in enumerate(options, start=1):
        candidates.append(
            _evaluate_candidate(courses, config, f"transfer_{index}", hours, config["credit_delta"])
        )
    events = []
    fallback = "unchanged"
    for candidate in candidates:
        identifier = candidate["candidate_id"]
        if candidate["feasible"]:
            fallback = identifier
        events.extend(
            [
                {
                    "candidate_id": identifier,
                    "stage": "generation",
                    "donor_course_id": config["donor_course_id"],
                    "target_course_id": config["target_course_id"],
                    "added_hours": candidate["added_hours"],
                    "credit_delta": candidate["credit_delta"],
                },
                {
                    "candidate_id": identifier,
                    "stage": "evaluation",
                    "status": candidate["status"],
                    "violations": list(candidate["violations"]),
                    "missing_inputs": list(candidate["missing_inputs"]),
                },
                {
                    "candidate_id": identifier,
                    "stage": "reflection",
                    "constraint_gaps": list(gaps),
                    "outcome_evidence": "学生掌握、就业率和起薪效果尚未识别",
                },
                {
                    "candidate_id": identifier,
                    "stage": "revision",
                    "revised_candidate_id": fallback,
                    "reason": "保留可行候选供教师审议"
                    if candidate["feasible"]
                    else "退回较小可行候选或原方案，补齐约束与材料后再审议",
                },
            ]
        )
    return {
        "schema_version": 1,
        "evidence_mode": plan["evidence_mode"],
        "coverage": plan["coverage"],
        "curriculum": copy.deepcopy(plan),
        "scenario_assumptions": copy.deepcopy(config),
        "baseline_candidate_id": "unchanged",
        "selected_candidate_id": "unchanged",
        "selection_rule": "默认保持原方案；可行性只覆盖已建模约束，可行候选交教师审议",
        "candidates": candidates,
        "review_candidate_ids": [row["candidate_id"] for row in candidates[1:] if row["feasible"]],
        "unverified_constraints": gaps,
        "process_log": events,
        "employment_effect": {
            "status": "unidentified",
            "missing_evidence": [
                "改革实施时间、覆盖学生与实际执行内容记录",
                "改革前后学生任务能力、固定毕业后时间窗就业率与起薪数据",
                "可比对照组、学生基础与同期政策，用于识别改革的因果效应",
                "调出课程的教学损失及课程间交互证据",
                "效果跨学校、专业与年级迁移的验证数据",
            ],
        },
        "assumptions": copy.deepcopy(config["assumption_notes"]),
        "limitations": [
            "结论只覆盖所选课程，完整培养方案的毕业要求、学分结构和外部先修未建模",
            "课时底线、学分底线与新增课时容量来自情景配置，需要教师核对",
            "已知先修要求按严格早于后续课程的学期检查；未公开关系和学期列入约束缺口",
            "目标课时增加只记录教学投入，学生掌握程度、就业率和起薪效果需要真实结果数据",
            "默认保留原方案只表示等待证据；基线是否满足情景约束由其检查结果单列",
        ],
    }
