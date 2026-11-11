"""Compare a bounded job sample with evidenced course text and explicit hypotheses."""

import copy
import math

from .curriculum import _number, _text


def _ratio(value, field):
    _number(value, field)
    if value > 1:
        raise ValueError(f"{field} 超出比例范围，请填写[0,1]内数值")


def _shares(value, families, field):
    if not isinstance(value, dict) or set(value) != set(families):
        raise ValueError(f"{field} 岗位族不完整，请逐项填写全部岗位族比例")
    for number in value.values():
        _ratio(number, field)
    if not math.isclose(math.fsum(value.values()), 1, rel_tol=0, abs_tol=1e-12):
        raise ValueError(f"{field} 比例和不为1，请检查方向结构与分母")


def _rows(value, field):
    if not isinstance(value, list):
        raise ValueError(f"{field} 格式错误，请填写对象列表")
    seen = set()
    for row in value:
        if not isinstance(row, dict):
            raise ValueError(f"{field} 项无效，请填写对象")
        _text(row.get("scenario_id"), f"{field}.scenario_id")
        if row["scenario_id"] in seen:
            raise ValueError(f"{field}.scenario_id 重复，请提供唯一情景ID")
        seen.add(row["scenario_id"])


def compare_supply_demand(program: dict, demand: dict, assumptions: dict) -> dict:
    """Retain text-coverage bounds, conditional direction errors and scale thresholds."""
    for name, value, mode in [
        ("program", program, "published_program_requirements"),
        ("demand", demand, "historical_sample"),
        ("assumptions", assumptions, "scenario_assumptions"),
    ]:
        if not isinstance(value, dict):
            raise ValueError(f"{name} 不是对象，请填写JSON对象")
        if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
            raise ValueError(f"{name}.schema_version 无效，请填写整数1")
        if value.get("evidence_mode") != mode:
            raise ValueError(f"{name}.evidence_mode 无效，请填写{mode}")
    for field in ["scope", "source"]:
        _text(demand.get(field), f"demand.{field}")
    total = demand.get("job_records")
    _number(total, "demand.job_records")
    if type(total) is not int:
        raise ValueError("demand.job_records 不是整数，请填写样本记录数")
    counts = {}
    for field in ["skill_counts", "job_family_counts"]:
        group = demand.get(field)
        if not isinstance(group, dict) or not group:
            raise ValueError(f"demand.{field} 缺项，请填写计数字典并保留零组")
        for key, number in group.items():
            _text(key, field)
            _number(number, field)
            if type(number) is not int or number > total:
                raise ValueError(f"demand.{field} 计数超出分母或非整数，请核对样本")
        counts[field] = sum(group.values())
        _number(counts[field], field)
    families = demand["job_family_counts"]
    if counts["job_family_counts"] != total:
        raise ValueError("job_family_counts 合计不等于job_records，请补齐互斥岗位族")
    courses = program.get("courses")
    if (
        not isinstance(courses, list)
        or not courses
        or not all(isinstance(row, dict) for row in courses)
    ):
        raise ValueError("program.courses 无效，请提供已核对的课程对象列表")
    course_ids = set()
    for row in courses:
        identifier = row.get("course_id")
        _text(identifier, "program.courses.course_id")
        if identifier in course_ids:
            raise ValueError("program.courses.course_id 重复，请核对课程目录")
        course_ids.add(identifier)
    links = assumptions.get("skill_links")
    if not isinstance(links, list):
        raise ValueError("skill_links 无效，请提供带课程ID与原文位置的列表")
    supported = set()
    seen_links = set()
    for row in links:
        if not isinstance(row, dict):
            raise ValueError("skill_links 项无效，请填写对象")
        for field in ["skill", "course_id", "source_location"]:
            _text(row.get(field), f"skill_links.{field}")
        key = (row["skill"], row["course_id"])
        if row["skill"] not in demand["skill_counts"] or row["course_id"] not in course_ids:
            raise ValueError("skill_links 引用了未知技能或课程，请核对需求词表与课程目录")
        if key in seen_links:
            raise ValueError("skill_links 关系重复，请保留唯一技能课程关系")
        supported.add(row["skill"])
        seen_links.add(key)
    planned = assumptions.get("planned_skills")
    if not isinstance(planned, list):
        raise ValueError("planned_skills 无效，请填写拟覆盖的技能列表")
    for skill in planned:
        _text(skill, "planned_skills")
        if skill not in demand["skill_counts"]:
            raise ValueError("planned_skills 引用了未知技能，请使用需求词表")
    if len(set(planned)) != len(planned):
        raise ValueError("planned_skills 重复，请保留唯一技能")
    _text(assumptions.get("assumption_source"), "assumption_source")
    _shares(assumptions.get("proposed_direction_shares"), families, "proposed_direction_shares")
    hypotheses = assumptions.get("baseline_direction_hypotheses")
    _rows(hypotheses, "baseline_direction_hypotheses")
    for row in hypotheses:
        _shares(row.get("shares"), families, "baseline_direction_hypotheses.shares")
    scale = assumptions.get("scale_scenarios")
    _rows(scale, "scale_scenarios")
    for row in scale:
        for field in ["cohort_index", "positions_per_record"]:
            _number(row.get(field), f"scale_scenarios.{field}")
        for field in ["jobseeker_fraction", "sample_access_share"]:
            _ratio(row.get(field), f"scale_scenarios.{field}")
    mentions = counts["skill_counts"]
    known_weight = math.fsum(demand["skill_counts"][skill] for skill in supported)
    proposed_weight = math.fsum(demand["skill_counts"][skill] for skill in supported | set(planned))
    direction_rows = []
    if total:
        actual = {key: count / total for key, count in families.items()}

        def distance(shares):
            return math.fsum(abs(shares[key] - actual[key]) for key in actual) / 2

        proposed_distance = distance(assumptions["proposed_direction_shares"])
        for row in hypotheses:
            baseline_distance = distance(row["shares"])
            direction_rows.append(
                {
                    "scenario_id": row["scenario_id"],
                    "baseline_tvd": baseline_distance,
                    "proposed_tvd": proposed_distance,
                    "improvement": baseline_distance - proposed_distance,
                    "positive_advantage": baseline_distance - proposed_distance > 1e-12,
                }
            )
    scale_rows = []
    for row in scale:
        try:
            denominator = total * row["positions_per_record"]
            opportunities = denominator * row["sample_access_share"]
            seekers = row["cohort_index"] * row["jobseeker_fraction"]
        except OverflowError as error:
            raise ValueError("scale_scenarios 乘积溢出，请缩小参数并核对指数单位") from error
        _number(opportunities, "scale_scenarios.opportunities")
        _number(seekers, "scale_scenarios.jobseekers")
        _number(denominator, "scale_scenarios.sample_positions")
        break_even = seekers / denominator if denominator else None
        if break_even is not None:
            _number(break_even, "scale_scenarios.break_even_sample_access_share")
        scale_rows.append(
            {
                **row,
                "conditional_opportunities": opportunities,
                "normalized_jobseekers": seekers,
                "opportunity_minus_jobseekers": opportunities - seekers,
                "break_even_sample_access_share": break_even,
            }
        )
    return {
        "schema_version": 1,
        "status": "conditional_proxy_analysis",
        "demand": copy.deepcopy(demand),
        "assumptions": copy.deepcopy(assumptions),
        "skills": {
            "measure": "job_mention_weighted_explicit_course_text_coverage",
            "mention_denominator": mentions,
            "baseline_coverage_interval": [known_weight / mentions, 1.0] if mentions else None,
            "proposed_coverage_interval": [proposed_weight / mentions, 1.0] if mentions else None,
            "proxy_gain_interval": [0.0, (proposed_weight - known_weight) / mentions]
            if mentions
            else None,
            "unknown_skills": sorted(set(demand["skill_counts"]) - supported),
            "gain_assumption": "既有名称证据保留，拟定内容按计划实施且没有内容覆盖损失",
            "status": "conditional_text_proxy" if mentions else "no_skill_mentions",
        },
        "directions": {
            "metric": "total_variation_distance",
            "advantage_zero_tolerance": 1e-12,
            "observed_school_gap": None,
            "conditional_comparisons": direction_rows,
        },
        "scale": {
            "measure": "sample_opportunities_minus_normalized_jobseekers",
            "actual_school_gap": None,
            "conditional_scenarios": scale_rows,
        },
        "student_mastery_effect": "unidentified",
        "limitations": [
            "需求来自限定岗位样本，平台覆盖和每条记录对应人数尚未校准。",
            "技能分母为词面提及总数，同一岗位可提及多个技能。",
            "课程关系为原文位置可追溯的显式内容证据，未证实的技能保留未知。",
            "课程目录中的选修可用性与学生实际修读分开，当前覆盖尚未按真实学生课表识别。",
            "拟覆盖内容和方向基线均为情景，未取得同校方向人数。",
            "规模使用规范化届别指数、求职比例和样本可达份额，实际学校缺口保持未知。",
            "课程文本覆盖增量、方向结构距离与条件规模差额分别度量，学生能力和就业收益另需识别。",
        ],
    }
