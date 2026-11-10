"""Project reported literature effects under explicit transfer and bias assumptions."""

import json
import math
from urllib.parse import urlparse

from chanjiao_evidence.evidence import parse_evidence


def _text(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} 缺少有效文字，请填写具体内容及来源")
    return value


def _text_list(value, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} 需要非空文字列表，请逐项填写来源位置")
    return [_text(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _number(value, field: str, lower: float = -math.inf, upper: float = math.inf) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} 需要有限数值，请使用原指标单位的数字")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"{field} 超出数值范围，请核对原文数值及单位") from error
    if not math.isfinite(number) or not lower <= number <= upper:
        raise ValueError(f"{field} 非有限数或超出允许范围，请核对数值、符号及原指标单位")
    return number


def _income_percent(estimate: float, interval: list[float]) -> dict:
    try:
        converted = [100 * math.expm1(value) for value in [estimate, *interval]]
    except OverflowError:
        converted = [math.inf]
    if not all(math.isfinite(value) for value in converted):
        return {"status": "outside_numeric_range", "estimate": None, "interval": None}
    return {
        "status": "derived_from_log_points",
        "estimate": converted[0],
        "interval": converted[1:],
        "unit": "relative_income_percent",
        "interpretation": (
            "由对数收入差通过100×expm1换算的相对收入百分比，结果限同一收入指标和时间窗"
        ),
    }


def evaluate_scenarios(evidence: dict, config: dict) -> dict:
    """Keep literature identification separate from target-population projections."""
    if not isinstance(evidence, dict):
        raise ValueError("evidence 应为 JSON 对象，请提供含 schema_version 和 cards 的文献输入")
    if not isinstance(config, dict):
        raise ValueError("config 应为 JSON 对象，请按 effect-scenarios.json 填写")
    if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        raise ValueError("config.schema_version 当前只支持整数1，请按v1情景示例导出")
    if config.get("evidence_mode") != "scenario_assumptions":
        raise ValueError("config.evidence_mode 必须标记 scenario_assumptions，请显式区分情景假设")
    for field in ["action_id", "target_population", "target_action"]:
        _text(config.get(field), f"config.{field}")
    applicability = config.get("applicability")
    if not isinstance(applicability, dict):
        raise ValueError("config.applicability 应为对象，请填写适用状态、理由及来源")
    if applicability.get("status") not in ("unverified", "supported", "mismatch"):
        raise ValueError("config.applicability.status 无效，请填 unverified、supported 或 mismatch")
    _text(applicability.get("rationale"), "config.applicability.rationale")
    _text_list(applicability.get("source_locations"), "config.applicability.source_locations")
    effect_reference = config.get("effect_reference")
    if not isinstance(effect_reference, dict):
        raise ValueError("config.effect_reference 应为对象，请指定 evidence_id 与 outcome_id")
    evidence_id = _text(effect_reference.get("evidence_id"), "config.effect_reference.evidence_id")
    outcome_id = _text(effect_reference.get("outcome_id"), "config.effect_reference.outcome_id")

    rows = config.get("scenarios")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError("config.scenarios 必须恰有三项，请填写 pessimistic、base、optimistic")
    scenarios = []
    for index, row in enumerate(rows):
        prefix = f"config.scenarios[{index}]"
        if not isinstance(row, dict):
            raise ValueError(f"{prefix} 应为对象，请填写情景ID、迁移系数、偏差及假设来源")
        scenarios.append(
            {
                "scenario_id": _text(row.get("scenario_id"), f"{prefix}.scenario_id"),
                "transfer_factor": _number(
                    row.get("transfer_factor"), f"{prefix}.transfer_factor", 0, 1
                ),
                "bias": _number(row.get("bias"), f"{prefix}.bias", 0),
                "assumption_source": _text(
                    row.get("assumption_source"), f"{prefix}.assumption_source"
                ),
            }
        )
    if {row["scenario_id"] for row in scenarios} != {"pessimistic", "base", "optimistic"}:
        raise ValueError("config.scenarios.scenario_id 缺失、重复或无效，请各填一次三个规定ID")

    if type(evidence.get("schema_version")) is not int or evidence["schema_version"] != 1:
        raise ValueError("evidence.schema_version 当前只支持整数1，请按文献卡片格式导出")
    cards = evidence.get("cards")
    if not isinstance(cards, list) or not all(isinstance(card, dict) for card in cards):
        raise ValueError("evidence.cards 应为对象列表，请按文献卡片格式填写")
    matches = [card for card in cards if card.get("evidence_id") == evidence_id]
    if len(matches) != 1:
        raise ValueError("effect_reference.evidence_id 未唯一匹配卡片，请核对ID并删除重复研究")
    card = matches[0]
    reported = card.get("reported_results")
    if not isinstance(reported, list) or not all(isinstance(row, dict) for row in reported):
        raise ValueError("evidence.reported_results 应为对象列表，请保留原指标、单位及原文位置")
    outcome_ids = [
        _text(row.get("outcome_id"), f"evidence.reported_results[{index}].outcome_id")
        for index, row in enumerate(reported)
    ]
    if len(set(outcome_ids)) != len(outcome_ids):
        raise ValueError("evidence.reported_results.outcome_id 重复，请为每个原指标保留唯一结果")
    matches = [row for row in reported if row.get("outcome_id") == outcome_id]
    if len(matches) != 1:
        raise ValueError("effect_reference.outcome_id 未唯一匹配结果，请核对原指标ID并删除重复结果")
    reported_result = matches[0]
    estimate = _number(reported_result.get("value"), "evidence.reported_results.value")
    unit = reported_result.get("unit")
    if unit not in ("log_points", "proportion_difference"):
        raise ValueError(
            "evidence.reported_results.unit 不支持，请保留 log_points 或 proportion_difference"
        )
    if unit == "proportion_difference" and not -1 <= estimate <= 1:
        raise ValueError("evidence.reported_results.value 比例差值越界，请以[-1,1]原始比例填写")
    standard_error = None
    ci95 = None
    if "standard_error" in reported_result:
        standard_error = _number(
            reported_result["standard_error"], "evidence.reported_results.standard_error", 0
        )
        ci95 = [
            _number(estimate - 1.96 * standard_error, "evidence.reported_results.ci95"),
            _number(estimate + 1.96 * standard_error, "evidence.reported_results.ci95"),
        ]
    _text(card.get("source_version"), "evidence.source_version")
    source_url = _text(
        reported_result.get("source_url", card.get("source_url")),
        "evidence.reported_results.source_url",
    )
    source = urlparse(source_url)
    if source.scheme != "https" or not source.netloc:
        raise ValueError("evidence.reported_results.source_url 无效，请填写原始来源的https链接")
    # Reuse the established literature-card boundary before exposing source details.
    try:
        content = json.dumps(evidence, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("evidence 含无效JSON值，请移除非有限数、超大整数及非JSON对象") from error
    parsed = parse_evidence(content, outcome_id)
    card = next(card for card in parsed["cards"] if card["evidence_id"] == evidence_id)
    reference = {
        **reported_result,
        "evidence_id": evidence_id,
        "standard_error": standard_error,
        "ci95": ci95,
        "source_version": card["source_version"],
        "title": card["title"],
        "source_url": source_url,
        "source_locations": card.get("source_locations", []),
        "population": card.get("population"),
        "action_id": card.get("action_id"),
        "action": card.get("action"),
        "design": card["design"],
        "assumptions": card.get("assumptions", []),
        "transfer_limits": card["transfer_limits"],
        "data_access": card.get("data_access", {}),
        "replication_status": "reported_literature_value",
    }
    reference_interval = ci95 if ci95 is not None else [estimate, estimate]
    interval_kind = "transferred_reference_normal_95" if ci95 is not None else "reported_value_only"
    advantage_tolerance = 1e-12
    records = []
    for index, scenario in enumerate(scenarios):
        factor = scenario["transfer_factor"]
        bias = scenario["bias"]
        prefix = f"config.scenarios[{index}]"
        projected = _number(factor * estimate - bias, f"{prefix}.estimate")
        if unit == "proportion_difference" and not -1 <= projected <= 1:
            raise ValueError(f"{prefix}.bias 使比例差点估计超出[-1,1]，请核对同单位偏差及迁移系数")
        interval = [
            _number(factor * endpoint - bias, f"{prefix}.interval")
            for endpoint in reference_interval
        ]
        record = {
            **scenario,
            "parameters_status": "scenario_assumptions",
            "estimate": projected,
            "interval": interval,
            "interval_kind": interval_kind,
            "unit": unit,
            "bias_unit": unit,
            "bias_thresholds": {
                "point_estimate": factor * estimate,
                "interval_lower": factor * reference_interval[0],
            },
            "positive_point_advantage": projected > advantage_tolerance,
            "positive_lower_advantage": interval[0] > advantage_tolerance,
        }
        if unit == "log_points" and outcome_id == "earnings":
            record["relative_income_percent"] = _income_percent(projected, interval)
        records.append(record)

    supported = applicability["status"] == "supported"
    status = "conditional_projection" if supported else "literature_reference_scenarios"
    missing = [
        "本校同定义措施的学生结果、人群、时间窗及可比对照尚未提供，无法识别本校已观察因果效果。",
        "迁移系数和偏差均为情景假设，需用本校可比改革或独立校准证据约束来源和范围。",
    ]
    if not supported:
        missing.append(
            "措施、人群和时间窗适用性尚未得到支持，请补齐逐项对应材料后再评价目标条件性效果。"
        )
    if standard_error is None:
        missing.append("所选论文报告值缺标准误，请取得同一估计的标准误或复现数据后计算抽样区间。")
    return {
        "schema_version": 1,
        "evidence_mode": "scenario_assumptions",
        "status": status,
        "action_id": config["action_id"],
        "target_population": config["target_population"],
        "target_action": config["target_action"],
        "applicability": {
            "status": applicability["status"],
            "rationale": applicability["rationale"],
            "source_locations": list(applicability["source_locations"]),
        },
        "target_effect": {
            "status": "conditional_projection" if supported else "unidentified",
            "observed_causal_effect": False,
        },
        "identification_status": (
            "reported_normal_95_reference_only"
            if ci95 is not None
            else "reported_value_only_no_sampling_ci"
        ),
        "reference": reference,
        "scenarios": records,
        "advantage_zero_tolerance": advantage_tolerance,
        "zero_effect_comparison": {"estimate": 0.0, "unit": unit},
        "formula": "transfer_factor * reported_effect - bias，同单位区间端点逐项计算",
        "threshold_interpretation": (
            "偏差达到对应阈值时增量为零。负阈值表示该参照已无正优势。阈值保留原指标单位。"
        ),
        "missing_evidence": missing,
        "limitations": [
            "文献报告值未在本项目中重估，抽样区间采用报告标准误的正态近似。",
            "区间只传播文献抽样范围和显式假设，不含迁移参数不确定性，无法作为本校效果置信区间。",
            "收入、面试邀请、就业率及学生能力分别度量，当前结果只覆盖所选原指标。",
            "收入百分比换算仅支持earnings收入指标，其他对数指标保留原名称和单位。",
            "正优势判据使用1e-12的绝对零容差，原始计算值与偏差阈值完整保留。",
            "比例差点估计限定[-1,1]。正态近似参考区间允许越过参数空间，端点保留统计近似含义。",
            "三情景名称不表示概率或保证顺序，零迁移、负值和无优势结果全部保留。",
        ],
    }
