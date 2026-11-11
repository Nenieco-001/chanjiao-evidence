"""Check declared student paths and retain auditable, unapproved policy scenarios."""

import copy
import math
from fractions import Fraction

from chanjiao_evidence.curriculum import (
    _finite_sum,
    _number,
    _text,
    _validate_inputs,
    evaluate_curriculum,
)


def _integer(value, field: str) -> None:
    _number(value, field)
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} 不是正整数，请填写大于零的整数")


def _ratio(value, field: str) -> None:
    _number(value, field)
    if value > 1:
        raise ValueError(f"{field} 超出比例范围，请填写 [0,1] 内的数值")


def _objects(value, field: str, identifier: str) -> list:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} 为空或格式无效，请填写非空对象列表")
    seen = set()
    for row in value:
        if not isinstance(row, dict):
            raise ValueError(f"{field} 项格式无效，请填写对象")
        _text(row.get(identifier), f"{field}.{identifier}")
        if row[identifier] in seen:
            raise ValueError(f"{field}.{identifier} 重复，请使用唯一标识")
        seen.add(row[identifier])
    return value


def _course_ids(value, field: str, course_modules: dict) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{field} 格式无效，请填写课程 ID 列表")
    seen = set()
    for identifier in value:
        _text(identifier, field)
        if identifier not in course_modules or identifier in seen:
            raise ValueError(f"{field} 含未知或重复课程 {identifier}，请核对专业课程映射")
        seen.add(identifier)


def _validate(config: dict, program: dict) -> None:
    for name, value, mode in [
        ("config", config, "scenario_assumptions"),
        ("program", program, "published_program_requirements"),
    ]:
        if not isinstance(value, dict):
            raise ValueError(f"{name} 格式无效，请填写 JSON 对象")
        if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
            raise ValueError(f"{name}.schema_version 无效，请填写整数 1")
        if value.get("evidence_mode") != mode:
            raise ValueError(f"{name}.evidence_mode 无效，请填写 {mode}")
    _number(program.get("minimum_total_credits"), "program.minimum_total_credits")
    modules = program.get("module_minimum_credits")
    if not isinstance(modules, dict) or not modules:
        raise ValueError("program.module_minimum_credits 缺失，请填写模块底线对象")
    for module, credits in modules.items():
        _text(module, "program.module_minimum_credits")
        _number(credits, f"program.module_minimum_credits.{module}")
    _finite_sum(modules.values(), "program.module_minimum_credits")
    course_modules = program.get("course_modules")
    if not isinstance(course_modules, dict) or not course_modules:
        raise ValueError("program.course_modules 缺失，请填写课程到模块的映射")
    for identifier, module in course_modules.items():
        _text(identifier, "program.course_modules")
        if not isinstance(module, str) or module not in modules:
            raise ValueError(
                f"program.course_modules.{identifier} 模块未知，请使用模块底线中的名称"
            )
    scenarios = _objects(config.get("curriculum_scenarios"), "curriculum_scenarios", "scenario_id")
    for row in scenarios:
        if not isinstance(row.get("config"), dict):
            raise ValueError("curriculum_scenarios.config 缺失，请提供课程情景对象")
    paths = _objects(config.get("student_paths"), "student_paths", "path_id")
    for path in paths:
        credits = path.get("module_credits")
        if not isinstance(credits, dict) or credits.keys() != modules.keys():
            raise ValueError("student_paths.module_credits 模块不完整，请逐项填写全部专业模块")
        for module, value in credits.items():
            _number(value, f"student_paths.module_credits.{module}")
        _finite_sum(credits.values(), "student_paths.module_credits")
        _course_ids(
            path.get("selected_course_ids"), "student_paths.selected_course_ids", course_modules
        )
    _integer(config.get("selection_semester"), "selection_semester")
    for direction in _objects(config.get("directions"), "directions", "direction_id"):
        for field in ["label", "job_family"]:
            _text(direction.get(field), f"directions.{field}")
        _integer(direction.get("capacity"), "directions.capacity")
        _ratio(direction.get("minimum_score"), "directions.minimum_score")
        _course_ids(direction.get("course_ids"), "directions.course_ids", course_modules)
        if not direction["course_ids"]:
            raise ValueError("directions.course_ids 为空，请填写方向关联课程")
    admissions = config.get("admissions")
    if not isinstance(admissions, dict):
        raise ValueError("admissions 缺失，请填写招生反馈配置")
    for field in [
        "baseline_enrollment",
        "minimum_enrollment",
        "maximum_enrollment",
        "observed_employment_rate",
        "observed_feedback_year",
    ]:
        if field not in admissions:
            raise ValueError(f"admissions.{field} 缺失，请填写数值，未知时填写 null")
    for field in [
        "baseline_enrollment",
        "minimum_enrollment",
        "maximum_enrollment",
        "observed_feedback_year",
    ]:
        if admissions[field] is not None:
            _integer(admissions[field], f"admissions.{field}")
    for field in ["target_rate", "max_relative_change"]:
        _ratio(admissions.get(field), f"admissions.{field}")
    _number(admissions.get("gain"), "admissions.gain")
    _integer(admissions.get("feedback_lag_years"), "admissions.feedback_lag_years")
    _integer(admissions.get("feedback_interval_years", 1), "admissions.feedback_interval_years")
    if admissions["observed_employment_rate"] is not None:
        _ratio(admissions["observed_employment_rate"], "admissions.observed_employment_rate")
    if admissions.get("evidence_mode", "historical") not in ("historical", "synthetic"):
        raise ValueError("admissions.evidence_mode 未知，请填写 historical 或 synthetic")
    minimum, maximum = admissions["minimum_enrollment"], admissions["maximum_enrollment"]
    baseline = admissions["baseline_enrollment"]
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("admissions.minimum_enrollment 大于 maximum_enrollment，请修正上下界")
    if baseline is not None and (
        (minimum is not None and baseline < minimum) or (maximum is not None and baseline > maximum)
    ):
        raise ValueError("admissions.baseline_enrollment 超出规模上下界，请核对原规模及边界")
    risks = _objects(config.get("risks"), "risks", "risk_id")
    if len(risks) < 3:
        raise ValueError("risks 少于三项，请填写至少三个不同风险及应对")
    action_ids = {row["scenario_id"] for row in scenarios} | {"directions", "admissions"}
    for risk in risks:
        for field in ["action_id", "impact", "owner", "trigger", "response"]:
            _text(risk.get(field), f"risks.{field}")
        if risk["action_id"] not in action_ids:
            raise ValueError("risks.action_id 未关联动作，请使用情景 ID、directions 或 admissions")
        bounds = risk.get("probability_range")
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError("risks.probability_range 无效，请填写 [下限,上限]")
        for value in bounds:
            _ratio(value, "risks.probability_range")
        if bounds[0] > bounds[1]:
            raise ValueError("risks.probability_range 顺序错误，请填写由小到大的比例范围")


def _path_result(path: dict, candidate: dict, scenario: dict, program: dict) -> dict:
    before = path["module_credits"]
    after = dict(before)
    violations = []
    if candidate["kind"] != "baseline":
        for role in ["donor", "target"]:
            identifier = scenario[f"{role}_course_id"]
            if identifier not in path["selected_course_ids"]:
                violations.append(f"{role}_not_selected:{identifier}")
        if not violations:
            deltas = {module: [credits] for module, credits in before.items()}
            deltas[program["course_modules"][scenario["donor_course_id"]]].append(
                -candidate["credit_delta"]
            )
            deltas[program["course_modules"][scenario["target_course_id"]]].append(
                candidate["credit_delta"]
            )
            after = {
                module: _finite_sum(values, f"student_paths.module_credits_after.{module}")
                for module, values in deltas.items()
            }
    for module, minimum in program["module_minimum_credits"].items():
        if after[module] < minimum:
            violations.append(f"module_minimum:{module}")
    total = _finite_sum(after.values(), "student_paths.total_credits_after")
    if total < program["minimum_total_credits"]:
        violations.append("minimum_total_credits")
    return {
        "path_id": path["path_id"],
        "status": "invalid" if violations else "valid",
        "violations": violations,
        "module_credits_before": dict(before),
        "module_credits_after": after,
        "total_credits_after": total,
    }


def _admissions(config: dict) -> dict:
    baseline = config["baseline_enrollment"]
    rate = config["observed_employment_rate"]
    year = config["observed_feedback_year"]
    result = {
        "status": "awaiting_inputs",
        "recommended_enrollment": baseline,
        "evidence_mode": config.get("evidence_mode", "historical"),
        "feedback_lag_years": config["feedback_lag_years"],
        "feedback_interval_years": config.get("feedback_interval_years", 1),
        "effective_intake_year": None,
        "next_intake_year": None,
        "expected_graduation_year": None,
        "relative_change": 0,
        "formula": (
            "clip(gain * (observed_employment_rate - target_rate), "
            "-max_relative_change, max_relative_change)"
        ),
        "interpretation": (
            "反馈观测年加调整周期作为适用招生年，招生年加培养时滞为预计毕业年。"
            "这是单周期限幅规则，长期闭环收敛尚未验证。就业时间窗需教务固定。"
        ),
    }
    if baseline is None or rate is None or year is None:
        return result
    cap = config["max_relative_change"]
    raw = config["gain"] * (rate - config["target_rate"])
    change = max(-cap, min(cap, raw))
    # Interpret the JSON decimal cap exactly before deriving integer capacity.
    try:
        allowed_change = math.floor(baseline * Fraction(str(cap)))
        lower = max(1, baseline - allowed_change, config["minimum_enrollment"] or 1)
        upper = min(baseline + allowed_change, config["maximum_enrollment"] or baseline * 2)
        if not math.isfinite(upper):
            raise ValueError("招生人数上界非有限值")
        proposed = max(lower, min(upper, math.floor(baseline * (1 + change) + 0.5)))
    except (OverflowError, ValueError) as error:
        raise ValueError("admissions 招生规模计算溢出，请缩小规模数值并检查单位") from error
    next_intake_year = year + config.get("feedback_interval_years", 1)
    result.update(
        status="conditional_recommendation",
        recommended_enrollment=proposed,
        effective_intake_year=next_intake_year,
        next_intake_year=next_intake_year,
        expected_graduation_year=next_intake_year + config["feedback_lag_years"],
        relative_change=(proposed - baseline) / baseline,
    )
    if result["evidence_mode"] == "synthetic":
        result.update(
            status="synthetic_stress_only",
            recommended_enrollment=baseline,
            synthetic_recommended_enrollment=proposed,
            relative_change=0,
        )
    return result


def evaluate_strategy(plan: dict, config: dict, program: dict) -> dict:
    """Recompute declared revisions on failures and expose all remaining evidence gaps."""
    _validate(config, program)
    scenario_results = []
    events = []
    termination = "revision_options_exhausted"
    scenarios = config["curriculum_scenarios"]
    # Validate all declared inputs, including revisions which may never activate.
    for scenario in scenarios:
        _validate_inputs(plan, scenario["config"])
        for field in ["school", "major", "program_version"]:
            if field in program and program[field] != plan[field]:
                raise ValueError(f"program.{field} 与课程输入不一致，请使用同校同专业同版本要求")
        for role in ["donor", "target"]:
            identifier = scenario["config"][f"{role}_course_id"]
            if identifier not in program["course_modules"]:
                raise ValueError(f"program.course_modules 缺少 {identifier}，请补齐课程模块映射")
    for index, scenario in enumerate(scenarios):
        events.append(
            {
                "stage": "generation",
                "scenario_id": scenario["scenario_id"],
                "config": copy.deepcopy(scenario["config"]),
            }
        )
        evaluation = evaluate_curriculum(plan, scenario["config"])
        candidates = []
        failures = []
        for candidate in evaluation["candidates"]:
            paths = [
                _path_result(path, candidate, scenario["config"], program)
                for path in config["student_paths"]
            ]
            status = "valid"
            if candidate["feasible"] is None:
                status = "not_evaluable"
            if candidate["feasible"] is False or any(row["violations"] for row in paths):
                status = "invalid"
            row = copy.deepcopy(candidate)
            row.update(curriculum_status=candidate["status"], status=status, student_paths=paths)
            candidates.append(row)
            if status != "valid":
                failures.append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "status": status,
                        "violations": candidate["violations"],
                        "student_paths": paths,
                        "missing_inputs": candidate["missing_inputs"],
                    }
                )
        scenario_results.append(
            {
                "scenario_id": scenario["scenario_id"],
                "candidates": candidates,
                "unverified_constraints": [
                    gap
                    for gap in evaluation["unverified_constraints"]
                    if gap != "unmodeled_program_credit_structure"
                ]
                + ["unmodeled_program_elective_subrequirements"],
            }
        )
        events.append(
            {
                "stage": "reflection",
                "scenario_id": scenario["scenario_id"],
                "failed_candidate_ids": [row["candidate_id"] for row in failures],
                "outcome_evidence": "学生能力与就业效果尚未识别，课程与模块可行性需教务审议",
            }
        )
        events.append(
            {
                "stage": "evaluation",
                "scenario_id": scenario["scenario_id"],
                "candidate_statuses": [
                    {"candidate_id": row["candidate_id"], "status": row["status"]}
                    for row in candidates
                ],
            }
        )
        if not failures:
            termination = "modeled_constraints_satisfied"
            break
        events.append(
            {
                "stage": "revision",
                "scenario_id": scenario["scenario_id"],
                "triggered_by": failures,
                "next_scenario_id": scenarios[index + 1]["scenario_id"]
                if index + 1 < len(scenarios)
                else None,
                "action": "recompute_next_scenario"
                if index + 1 < len(scenarios)
                else "stop_and_retain_failure",
            }
        )
    events.append({"stage": "termination", "reason": termination})
    risks = [
        dict(copy.deepcopy(row), evidence_mode="scenario_assumptions") for row in config["risks"]
    ]
    return {
        "schema_version": 1,
        "evidence_mode": "scenario_assumptions",
        "program_requirements": copy.deepcopy(program),
        "scenario_assumptions": copy.deepcopy(config),
        "scenario_results": scenario_results,
        "process_log": events,
        "termination_reason": termination,
        "selected_candidate_id": "unchanged",
        "approval_status": "pending_school_review",
        "direction_policy": {
            "status": "pending_review",
            "selection_semester": config["selection_semester"],
            "directions": copy.deepcopy(config["directions"]),
            "assignments": [],
            "score_unit": "proportion",
            "score_course_ids": [
                course["course_id"]
                for course in plan["courses"]
                if course["semester"] is not None
                and course["semester"] < config["selection_semester"]
            ],
            "score_definition": "分流学期前已修切片课程成绩归一化后等权平均，为待审假设",
            "steps": [
                "学生提交方向志愿并核验评分课程成绩，方向关联课程用于培养安排",
                "达到最低分者按志愿与方向分数从高到低录取至容量上限",
                "同分由教务公开审核，超额或未达线学生进入第二志愿及人工调剂",
                "调剂需学生确认并核对毕业模块学分；保留申诉与复核记录",
            ],
        },
        "admissions": _admissions(config["admissions"]),
        "risk_matrix": risks,
        "unknowns": [
            "选课路径为情景假设，需同届真实匿名选课与毕业审核记录核对",
            "师资、实验资源、方向容量和课程内容承接需学校审核",
            "先修关系需课程大纲；公开切片未覆盖完整课程执行要求",
            "完整必修选课、通识子类别及选修组合需完整学生课表逐项审核，模块总数仅覆盖已建模底线",
            "方向评分口径、学生志愿和实际分流人数缺少授权汇总材料",
            "同专业招生规模及固定毕业后时间窗就业观测需校内授权汇总",
            "就业反馈与招生变化的因果关系未识别，四年培养时滞内环境可能变化",
            "课程调整尚缺能力、就业及被替代内容损失的对照证据",
        ],
        "employment_effect": {"status": "unidentified"},
    }
