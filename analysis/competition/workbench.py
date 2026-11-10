"""窄题需求侧分析；Python 3.11–3.13，仅标准库，输入只读。"""

import argparse
import csv
import hashlib
import html
import json
import math
import re
import shutil
import statistics
import tempfile
import time
from collections import Counter
from datetime import date
from pathlib import Path

YEARS = (2016, 2023, 2026)
SUPPORTED_YEARS = (2016, 2023, 2024, 2025, 2026)
CITIES = ("北京", "上海")
INDUSTRIES = ("计算机、通信和其他电子设备制造业", "软件和信息技术服务业")
# 以下词面均在本机三个年度的描述探查中实际命中；不是外部标准技能本体。
SKILLS = (
    "Python",
    "Java",
    "JavaScript",
    "SQL",
    "C++",
    "Linux",
    "Git",
    "Docker",
    "机器学习",
    "深度学习",
    "数据结构",
    "软件测试",
)
PATTERNS = {
    term: (
        re.compile(r"(?<![A-Za-z0-9_])" + re.escape(term) + r"(?![A-Za-z0-9_+])", re.I)
        if term.isascii()
        else re.compile(re.escape(term))
    )
    for term in SKILLS
}
SCHEMA_MEANING = {
    2016: {"招聘类别": "职业分类", "初级分类": "职业分类，缺失较多"},
    2023: {"招聘类别": "主要为用工类型/不限，混有行业值", "初级分类": "主要为用工类型，混有岗位值"},
    2024: {
        "招聘类别": "按平台混合：平台2/4为行业，平台13为用工类型，平台10多为不限",
        "初级分类": "平台4主要为用工类型、混有岗位名；平台2多缺失或-，平台13/10缺失",
    },
    2025: {
        "招聘类别": "按平台混合：平台2/4为行业，平台10多为不限，平台100为社招/校招",
        "初级分类": "岗位名、缺失或-；平台4已不再主要是用工类型，平台100缺失",
    },
    2026: {"招聘类别": "行业标签", "初级分类": "岗位名"},
}
FIELDS = (
    "企业名称",
    "招聘岗位",
    "工作城市",
    "上市公司行业",
    "招聘发布年份",
    "招聘发布日期",
    "最低月薪",
    "最高月薪",
    "职位描述",
    "学历要求",
    "要求经验",
    "招聘类别",
    "初级分类",
    "来源",
)
MISSING = {"", "nan", "null", "none", "na", "n/a"}


def missing(value):
    return value.strip().lower() in MISSING


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def extract_skills(text):
    """返回词面和字符跨度；有限的前置否定只用于暴露规则失败边界。"""
    hits = []
    for skill, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            clause = re.split(r"[，,。；;\n]", text[: match.start()])[-1][-12:]
            rejected = bool(re.search(r"无需|不要求|不需要|不必", clause))
            hits.append(
                {
                    "skill": skill,
                    "surface": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "accepted": not rejected,
                    "reason": "前置否定，待人工复核" if rejected else "词面提及，不代表熟练度",
                }
            )
    return sorted(hits, key=lambda hit: (hit["start"], hit["skill"]))


def job_family(title):
    """保守岗位族代理；没有专业字段，不能据此认定该岗位招目标专业。"""
    if re.search(r"销售|招聘|猎头|硬件|电气|机械|工艺|生产|采购", title):
        return None
    for family, pattern in (
        ("软件测试", r"软件测试|测试开发|软件质量"),
        ("算法与机器学习", r"算法|机器学习|深度学习|人工智能"),
        ("数据分析与工程", r"数据分析|数据开发|数据工程|大数据|数据库"),
        ("系统运维与安全", r"运维|信息安全|网络安全|系统安全"),
        ("软件开发", r"软件|程序员|前端|后端|嵌入式|全栈|(?i:java|python|c\+\+|android|ios)"),
    ):
        if re.search(pattern, title):
            return family
    return None


def salary_midpoint(low, high):
    try:
        low, high = float(low), float(high)
    except ValueError:
        return None
    if not (math.isfinite(low) and math.isfinite(high) and 0 < low <= high):
        return None
    return (low + high) / 2


def education(raw):
    if missing(raw):
        return "缺失"
    if raw in ("不限", "学历不限", "无要求", "面议"):
        return "不限/未明确"
    if raw in ("中专", "技校", "中技", "中专,技校", "中专/中技", "中技/中专"):
        return "中等职业教育"
    if raw in ("初中", "初中及以下"):
        return "初中及以下"
    if raw in ("本科", "大专", "硕士", "博士", "高中"):
        return raw
    return "其他未映射"


def curriculum_gap(plan, demand):
    """最小接口只列课程词面覆盖，不将学时与招聘比例相减。"""
    if plan.get("evidence_mode") != "synthetic" or plan.get("label") != "示例占位":
        raise ValueError("本接口只接受 synthetic 且 label 为‘示例占位’；真实培养方案另行核验。")
    covered = set()
    for course in plan["courses"]:
        if (
            not isinstance(course["hours"], (int, float))
            or not math.isfinite(course["hours"])
            or course["hours"] < 0
        ):
            raise ValueError("课程 hours 必须是非负有限学时，请按课程大纲填写。")
        for skill in course["skill_mentions"]:
            if skill not in SKILLS:
                raise ValueError("课程技能不在本轮词表中，请先核验词面来源再扩充规则和测试。")
            covered.add(skill)
    return {
        "evidence_mode": "synthetic",
        "label": "示例占位",
        "not_a_learning_effect": True,
        "uncovered_mentions": sorted(set(demand) - covered),
        "covered_mentions": sorted(set(demand) & covered),
        "interpretation": "仅演示岗位词面与课程词面的集合差；不度量学生能力、缺课学时或就业效果。",
    }


def _new_group():
    return {"n": 0, "descriptions": 0, "skills": Counter(), "structures": {}, "salaries": []}


def _quantile(values, probability):
    index = (len(values) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def _analyse(year, path, evidence, records=None):
    groups = {scope: _new_group() for scope in ("两市合计", *CITIES)}
    summary = dict.fromkeys(
        (
            "source_rows",
            "selected_before_dedup",
            "duplicate_rows",
            "selected_rows",
            "description_nonmissing",
            "salary_valid",
            "year_or_date_excluded",
            "trailing_nonempty_excluded",
            "missing_company_key",
        ),
        0,
    )
    source_missing, cohort_missing, semantic = Counter(), Counter(), {}
    platforms, selected_platforms, seen, examples = Counter(), Counter(), set(), Counter()
    dates = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        columns = [name for name in header if name]
        if len(columns) != len(set(columns)) or not set(FIELDS).issubset(columns):
            absent = sorted(set(FIELDS) - set(columns))
            raise ValueError(
                f"{path.name} 缺少字段或表头重复：{'、'.join(absent)}；请保留原始列名。"
            )
        if any(name == "" for name in header[:-1]):
            raise ValueError(f"{path.name} 中间存在空列名；只允许末尾空列，请核对表头。")
        for record_index, values in enumerate(reader, start=1):
            if len(values) != len(header):
                raise ValueError(f"{path.name} 第 {record_index} 条记录列数异常；请修正 CSV。")
            row = {
                key: value if key == "职位描述" else value.strip()
                for key, value in zip(header, values, strict=True)
                if key
            }
            summary["source_rows"] += 1
            source_missing.update(key for key in FIELDS if missing(row[key]))
            platforms[row["来源"] or "缺失"] += 1
            for key in ("招聘类别", "初级分类"):
                semantic.setdefault(key, Counter())[row[key] or "缺失"] += 1
            if header[-1] == "" and values[-1].strip():
                summary["trailing_nonempty_excluded"] += 1
                continue
            try:
                published = date.fromisoformat(row["招聘发布日期"])
                valid = (
                    re.fullmatch(rf"{year}(?:\.0+)?", row["招聘发布年份"]) is not None
                    and published.year == year
                    and (year != 2026 or published <= date(2026, 3, 10))
                )
            except ValueError:
                valid = False
            if not valid:
                summary["year_or_date_excluded"] += 1
                continue
            dates.append(published.isoformat())
            city = row["工作城市"].removesuffix("市")
            family = job_family(row["招聘岗位"])
            if city not in CITIES or row["上市公司行业"] not in INDUSTRIES or family is None:
                continue
            summary["selected_before_dedup"] += 1
            key = tuple(
                row[k] for k in ("企业名称", "招聘岗位", "招聘发布日期", "最低月薪", "最高月薪")
            ) + (city,)
            if missing(row["企业名称"]):
                summary["missing_company_key"] += 1
            elif key in seen:
                summary["duplicate_rows"] += 1
                continue
            else:
                seen.add(key)
            summary["selected_rows"] += 1
            cohort_missing.update(key for key in FIELDS if missing(row[key]))
            selected_platforms[row["来源"] or "缺失"] += 1
            description = row["职位描述"]
            present = not missing(description)
            hits = extract_skills(description) if present else []
            skills = {hit["skill"] for hit in hits if hit["accepted"]}
            salary = salary_midpoint(row["最低月薪"], row["最高月薪"])
            summary["description_nonmissing"] += int(present)
            summary["salary_valid"] += int(salary is not None)
            if records is not None:
                # 仅留紧凑特征在内存；企业和岗位标识散列后只输出重叠数量。
                company = "" if missing(row["企业名称"]) else row["企业名称"]
                degree = education(row["学历要求"])
                records.append(
                    {
                        "platform": "" if missing(row["来源"]) else row["来源"],
                        "month": f"{published.month:02d}",
                        "city": city,
                        "industry": row["上市公司行业"],
                        "education": "" if degree in ("缺失", "其他未映射") else degree,
                        "experience": "" if missing(row["要求经验"]) else row["要求经验"],
                        "family": family,
                        "skills": sorted(skills),
                        "salary": salary,
                        "description": present,
                        "company_key": (
                            hashlib.sha256(company.encode("utf-8")).hexdigest() if company else None
                        ),
                        "job_key": (
                            hashlib.sha256(
                                json.dumps(
                                    [company, row["招聘岗位"], city], ensure_ascii=False
                                ).encode("utf-8")
                            ).hexdigest()
                            if company
                            else None
                        ),
                    }
                )
            for scope in ("两市合计", city):
                group = groups[scope]
                group["n"] += 1
                group["descriptions"] += int(present)
                group["skills"].update(skills)
                if salary is not None:
                    group["salaries"].append(salary)
                salary_bin = (
                    "无有效区间"
                    if salary is None
                    else (
                        "<10000"
                        if salary < 10000
                        else ("10000–19999" if salary < 20000 else ">=20000")
                    )
                )
                for dimension, value in (
                    ("岗位族", family),
                    ("城市", city),
                    ("上市公司行业", row["上市公司行业"]),
                    ("学历", education(row["学历要求"])),
                    ("经验原文", row["要求经验"] or "缺失"),
                    ("月薪区间中点分箱", salary_bin),
                ):
                    group["structures"].setdefault(dimension, Counter())[value] += 1
            for hit in hits:
                example_key = hit["skill"], hit["accepted"]
                if examples[example_key] >= 2:
                    continue
                examples[example_key] += 1
                # 不复制企业/地址/联系方式/描述片段。凭 CSV 记录序号与字符跨度本机复核。
                evidence.append(
                    {
                        "year": year,
                        "source_file": path.name,
                        "csv_record_index": record_index,
                        **hit,
                    }
                )
    n = summary["selected_rows"]
    summary.update(
        {
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
            "source_missing": {
                key: {
                    "n": source_missing[key],
                    "rate": (
                        source_missing[key] / summary["source_rows"]
                        if summary["source_rows"]
                        else None
                    ),
                }
                for key in FIELDS
            },
            "selected_missing": {
                key: {"n": cohort_missing[key], "rate": cohort_missing[key] / n if n else None}
                for key in FIELDS
            },
            "platforms_source": dict(sorted(platforms.items())),
            "platforms_selected": dict(sorted(selected_platforms.items())),
            "category_semantics": SCHEMA_MEANING[year],
            "category_examples": {key: counter.most_common(8) for key, counter in semantic.items()},
            "columns": header,
            "input_sha256": sha256(path),
            "input_bytes": path.stat().st_size,
        }
    )
    return summary, groups


def _chart(path, year, group):
    top = sorted(group["skills"].items(), key=lambda item: (-item[1], item[0]))[:8]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="820" height="420" viewBox="0 0 820 420">',
        '<rect width="820" height="420" fill="white"/>',
        f'<text x="24" y="32" font-size="20">{year} 年内技能词面提及 / 两市目标切片</text>',
        f'<text x="24" y="58" font-size="13">去重岗位 n={group["n"]}；'
        "比例以全部岗位为分母；不作跨年趋势</text>",
    ]
    for i, (skill, count) in enumerate(top):
        y = 90 + i * 36
        share = count / group["n"] if group["n"] else 0
        parts.extend(
            [
                f'<text x="24" y="{y + 17}" font-size="14">{html.escape(skill)}</text>',
                f'<rect x="150" y="{y}" width="{share * 480:.2f}" height="24" fill="#285a75"/>',
                f'<text x="{160 + share * 480:.2f}" y="{y + 17}" font-size="13">'
                f"{count} / {share:.1%}</text>",
            ]
        )
    parts.append(
        '<text x="24" y="408" font-size="12">历史招聘文本；上市公司样本；'
        "词面出现不代表能力或课程效果。</text></svg>"
    )
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _profile(group):
    n = group["n"]
    families = ("软件开发", "软件测试", "算法与机器学习", "数据分析与工程", "系统运维与安全")
    counts = group["structures"].get("岗位族", {})
    return {
        "n": n,
        "description_nonmissing": group["descriptions"],
        "families": {key: counts.get(key, 0) / n if n else None for key in families},
        "skills": {key: group["skills"].get(key, 0) / n if n else None for key in SKILLS},
        "salary_median": statistics.median(group["salaries"]) if group["salaries"] else None,
        "salary_valid": len(group["salaries"]),
        "salary_coverage": len(group["salaries"]) / n if n else None,
    }


def _prediction_metrics(prediction, actual):
    metrics = {"prediction": prediction}
    for field, label in (("families", "family"), ("skills", "skill")):
        predicted, observed = prediction[field], actual[field]
        comparable = all(v is not None for v in (*predicted.values(), *observed.values()))
        errors = [abs(predicted[k] - observed[k]) for k in observed] if comparable else []
        metrics[f"{label}_mae"] = statistics.mean(errors) if errors else None
        if field == "families":
            metrics["family_tvd"] = sum(errors) / 2 if errors else None
        else:
            # 零提及不挤进 Top-5；并列按技能名排序，重叠率固定除以 5。
            tops = [
                sorted(
                    (k for k, v in rates.items() if v is not None and v > 0),
                    key=lambda k: (-rates[k], k),
                )[:5]
                for rates in (predicted, observed)
            ]
            metrics["skill_top5_predicted"], metrics["skill_top5_actual"] = tops
            overlap = len(set(tops[0]) & set(tops[1])) if comparable else None
            metrics["skill_top5_overlap_n"] = overlap
            metrics["skill_top5_overlap_rate"] = overlap / 5 if overlap is not None else None
    predicted, observed = prediction["salary_median"], actual["salary_median"]
    error = abs(predicted - observed) if predicted is not None and observed is not None else None
    metrics["salary_absolute_error"] = error
    metrics["salary_relative_error"] = error / observed if error is not None else None
    return metrics


def _backtest_methods(training, actual):
    latest = training[-1]
    prediction = {}
    for field in ("families", "skills"):
        prediction[field] = {}
        for key in latest[field]:
            values = [p[field][key] for p in training if p[field][key] is not None]
            prediction[field][key] = statistics.mean(values) if values else None
    values = [p["salary_median"] for p in training if p["salary_median"] is not None]
    prediction["salary_median"] = statistics.mean(values) if values else None
    methods = {
        "latest_year": _prediction_metrics(latest, actual),
        "annual_mean": _prediction_metrics(prediction, actual),
    }
    for metrics in methods.values():
        metrics["improves_baseline"] = {
            key: (
                metrics[key] < methods["latest_year"][key]
                if metrics[key] is not None and methods["latest_year"][key] is not None
                else None
            )
            for key in ("family_mae", "skill_mae", "salary_absolute_error")
        }
    return methods


def retrospective_backtest(year_groups):
    """冻结的朴素基线；年份等权均值不按样本数加权，也不是因果估计。"""
    profiles = {year: _profile(group) for year, group in sorted(year_groups.items())}
    folds = []
    for target in (2024, 2025):
        train_years = [year for year in profiles if year < target]
        training = [profiles[year] for year in train_years]
        actual = profiles[target]
        methods = _backtest_methods(training, actual)
        folds.append(
            {
                "target_year": target,
                "cutoff_year": target - 1,
                "train_years": train_years,
                "empty_train_years": [year for year in train_years if not profiles[year]["n"]],
                "actual": actual,
                "methods": methods,
            }
        )
    return {
        "evidence_mode": "historical",
        "evaluation": "回顾性回测；2026已参与规则探索，不是未触碰留出",
        "baseline": "latest_year",
        "annual_mean": "可用年份的结构等权均值；薪资为有效年度中位数的均值，空年度不补零",
        "slice": "年度原切片；未匹配来源、月份或企业，不解释为市场趋势或培养效果",
        "rate_unit": "比例差，0.01 = 1个百分点；技能以全部去重岗位为分母",
        "folds": folds,
    }


MATCH_DIMENSIONS = ("platform", "month", "city", "industry", "education", "experience")
ERROR_DIMENSIONS = ("city", "industry", "platform", "education", "experience")


def _record_profile(records):
    group = _new_group()
    group["n"] = len(records)
    group["descriptions"] = sum(row["description"] for row in records)
    group["structures"]["岗位族"] = Counter(row["family"] for row in records)
    for row in records:
        group["skills"].update(row["skills"])
    group["salaries"] = [row["salary"] for row in records if row["salary"] is not None]
    return _profile(group)


def _slice_metrics(records, original, train_years, target):
    profiles = {year: _record_profile(rows) for year, rows in records.items()}
    actual = profiles[target]
    supported = all(profile["n"] for profile in profiles.values())
    training = [profiles[year] for year in train_years]
    # 空组仍输出两个方法及 null 指标，不借用其他组或全年分数。
    methods = _backtest_methods(training if supported else [_record_profile([])], actual)
    for method in methods.values():
        for key, higher in (
            ("family_tvd", False),
            ("skill_top5_overlap_rate", True),
            ("salary_relative_error", False),
        ):
            value, baseline = method[key], methods["latest_year"][key]
            method["improves_baseline"][key] = (
                (value > baseline if higher else value < baseline)
                if value is not None and baseline is not None
                else None
            )
    return {
        "status": "supported" if supported else "no_common_support",
        "actual": actual,
        "training": {str(year): profiles[year] for year in train_years},
        "n": actual["n"],
        "original_n": len(original[target]),
        "coverage": actual["n"] / len(original[target]) if original[target] else None,
        "description_coverage": (
            actual["description_nonmissing"] / actual["n"] if actual["n"] else None
        ),
        "small_sample": any(profile["n"] < 30 for profile in profiles.values()),
        "methods": methods,
    }


def _error_groups(records, original, train_years, target):
    groups = []
    for dimension in ERROR_DIMENSIONS:
        values = {row[dimension] for rows in original.values() for row in rows}
        if dimension == "city":
            values.update(CITIES)
        elif dimension == "industry":
            values.update(INDUSTRIES)
        for value in sorted(values):
            before = {
                year: [row for row in rows if row[dimension] == value]
                for year, rows in original.items()
            }
            after = {
                year: [row for row in rows if row[dimension] == value]
                for year, rows in records.items()
            }
            groups.append(
                {
                    "dimension": dimension,
                    "value": value or "缺失/未映射",
                    **_slice_metrics(after, before, train_years, target),
                    "share_of_matched_target": (
                        len(after[target]) / len(records[target]) if records[target] else None
                    ),
                }
            )
    return groups


def _leakage(original, matched, train_years, target):
    result = {}
    for field, label in (("company_key", "company"), ("job_key", "job")):
        training = {row[field] for year in train_years for row in original[year] if row[field]}
        for prefix, rows in (("", original[target]), ("matched_", matched[target])):
            hits = sum(row[field] in training for row in rows if row[field])
            result[f"{prefix}target_{label}_overlap_n"] = hits
            result[f"{prefix}target_{label}_overlap_rate"] = hits / len(rows) if rows else None
        result[f"target_missing_{label}_key_n"] = sum(not row[field] for row in original[target])
    result["definition"] = (
        "在原年度目标切片中：企业精确去首尾空白同名；疑似重复岗位=同企业+岗位原名+城市，"
        "忽略日期/薪资/来源。计数为目标记录数，同一企业多岗位可重复计；不是确认转发。"
        "matched计数仍对照全部训练切片，不隔离企业；只输出计数，不输出标识。"
    )
    return result


def comparable_backtest(year_records):
    """按所有训练年和目标年共同协变量支持切片；只做回顾性描述。"""
    folds = []
    for target in (2024, 2025):
        train_years = sorted(year for year in year_records if year < target)
        years = [*train_years, target]
        original = {year: year_records[year] for year in years}
        current = original.copy()
        stages, stopped_at = [], None
        for dimension in (*MATCH_DIMENSIONS, "joint_cell"):
            if dimension == "joint_cell":

                def key(row):
                    return tuple(row[field] for field in MATCH_DIMENSIONS)

            else:

                def key(row, field=dimension):
                    return row[field]

            supports = [{key(row) for row in current[year] if key(row)} for year in years]
            common = set.intersection(*supports)
            filtered = {
                year: [row for row in rows if key(row) in common] for year, rows in current.items()
            }
            stages.append(
                {
                    "dimension": dimension,
                    "common_values": sorted(common) if dimension != "joint_cell" else None,
                    "common_value_n": len(common),
                    "samples": {
                        str(year): {
                            "before_n": len(current[year]),
                            "missing_n": sum(not key(row) for row in current[year]),
                            "original_missing_n": (
                                sum(not row[dimension] for row in original[year])
                                if dimension != "joint_cell"
                                else sum(
                                    any(not row[field] for field in MATCH_DIMENSIONS)
                                    for row in original[year]
                                )
                            ),
                            "n": len(filtered[year]),
                            "coverage": (
                                len(filtered[year]) / len(original[year])
                                if original[year]
                                else None
                            ),
                            "retention": (
                                len(filtered[year]) / len(current[year]) if current[year] else None
                            ),
                        }
                        for year in years
                    },
                }
            )
            current = filtered
            if not common:
                stopped_at = dimension
                break
        folds.append(
            {
                "target_year": target,
                "cutoff_year": target - 1,
                "train_years": train_years,
                "original_samples": {
                    str(year): {
                        "n": len(original[year]),
                        "missing": {
                            field: sum(not row[field] for row in original[year])
                            for field in MATCH_DIMENSIONS
                        },
                    }
                    for year in years
                },
                **_slice_metrics(current, original, train_years, target),
                "stopped_at": stopped_at,
                "unreached_layers": list((*MATCH_DIMENSIONS, "joint_cell")[len(stages) :]),
                "stages": stages,
                "groups": _error_groups(current, original, train_years, target),
                "full_year": {
                    **_slice_metrics(original, original, train_years, target),
                    "groups": _error_groups(original, original, train_years, target),
                },
                "leakage": _leakage(original, current, train_years, target),
            }
        )
    return {
        "schema_version": 1,
        "evidence_mode": "historical",
        "baseline": "latest_year",
        "support_rule": (
            "按platform/month/city/industry/education/experience顺序取所有训练年和目标年的交集，"
            "最后取六维完整组合交集；每年各自保留原权重，不平衡各年或各月样本数。"
            "月度使用逐层收缩后的共同月份；不是固定1–3月，不评价2026。缺失/未映射不算支持。"
        ),
        "group_rule": (
            "单维误差组枚举原切片各年取值并集及固定城市/行业，含匹配后空组。coverage=组内匹配n/"
            "目标年该组原n；总coverage=匹配n/目标年原n；原n=0则null；小样本=任一年n<30，"
            "仅描述提示，不是显著性门槛。经验保留原文精确层，不合并近义类目。"
        ),
        "leakage_risks": [
            "匿名平台同号只是标签匹配，缺平台身份与采集规则说明，不能确认同源。",
            "支持选择查看了目标年协变量，是回顾性可比性诊断，不是事前可部署评价。",
            "2026已参与词表/规则探索；未进入预测计算，也不是未触碰留出。",
            "企业/岗位跨年疑似重复未隔离，年内跨平台去重保留首遇来源，可能改变平台归属。",
            "岗位与技能分组依赖探索规则，尚无独立人工标签；零提及不代表无技能要求。",
        ],
        "cannot_conclude": [
            "样本外误差不等于真实因果；不能推断课程改革的就业率、起薪或能力效果。",
            "共同支持不代表代表性或同等采样；不能推断市场总量、趋势或全部学校。",
            "企业重叠不证明复制，低误差不证明独立泛化；不支持四年前瞻准确性声明。",
        ],
        "folds": folds,
    }


def run(inputs, output, *, backtest=False, matched_backtest=False):
    backtest = backtest or matched_backtest
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"输出路径已存在：{output}；请换一个新目录，已有产物不覆盖。")
    if not inputs or any(year not in SUPPORTED_YEARS for year in inputs):
        raise ValueError("请选择 2016/2023/2024/2025/2026 年度 CSV；其他年份需先核验 schema。")
    if backtest and not {2023, 2024, 2025}.issubset(inputs):
        raise ValueError("回测需明确提供 2023、2024、2025 年度 CSV；2016 可选，2026 不参与预测。")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent))
    try:
        summary = {
            "schema_version": 1,
            "evidence_mode": "historical",
            "target_major": "计算机科学与技术（岗位族代理，非直接专业匹配）",
            "cities": CITIES,
            "industries": INDUSTRIES,
            "years": {},
            "cross_year_total_trend": False,
            "salary_unit": "元/月，原字段单位，区间中点非起薪",
            "holdout_status": "2026 已用于探索，不再是未触碰留出；正式评价需冻结规则和独立样本",
        }
        structures, skills_rows, salaries, evidence = [], [], [], []
        annual_groups, annual_records = {}, {}
        for year, path in sorted(inputs.items()):
            records = [] if matched_backtest else None
            sample, groups = _analyse(year, Path(path), evidence, records)
            if records is not None:
                annual_records[year] = records
            annual_groups[year] = groups
            summary["years"][str(year)] = sample
            for scope, group in groups.items():
                n = group["n"]
                for dimension, counter in sorted(group["structures"].items()):
                    for category, count in sorted(counter.items()):
                        structures.append(
                            {
                                "year": year,
                                "scope": scope,
                                "dimension": dimension,
                                "category": category,
                                "n": count,
                                "denominator": n,
                                "share": count / n,
                            }
                        )
                for skill in SKILLS:
                    count = group["skills"][skill]
                    skills_rows.append(
                        {
                            "year": year,
                            "scope": scope,
                            "skill": skill,
                            "n": count,
                            "all_jobs": n,
                            "nonmissing_descriptions": group["descriptions"],
                            "share_all_jobs": count / n if n else None,
                            "share_nonmissing_descriptions": (
                                count / group["descriptions"] if group["descriptions"] else None
                            ),
                        }
                    )
                values = sorted(group["salaries"])
                salaries.append(
                    {
                        "year": year,
                        "scope": scope,
                        "all_jobs": n,
                        "valid_intervals": len(values),
                        "invalid_or_missing": n - len(values),
                        "p25": _quantile(values, 0.25) if values else None,
                        "median_midpoint": statistics.median(values) if values else None,
                        "p75": _quantile(values, 0.75) if values else None,
                    }
                )
            _chart(temporary / f"skills-{year}.svg", year, groups["两市合计"])
        if backtest:
            write_json(
                temporary / "backtest.json",
                {
                    "scopes": {
                        scope: retrospective_backtest(
                            {year: groups[scope] for year, groups in annual_groups.items()}
                        )
                        for scope in ("两市合计", *CITIES)
                    }
                },
            )
        if matched_backtest:
            write_json(temporary / "matched-backtest.json", comparable_backtest(annual_records))
        write_json(temporary / "summary.json", summary)
        write_csv(
            temporary / "structures.csv",
            ("year", "scope", "dimension", "category", "n", "denominator", "share"),
            structures,
        )
        write_csv(
            temporary / "skills.csv",
            (
                "year",
                "scope",
                "skill",
                "n",
                "all_jobs",
                "nonmissing_descriptions",
                "share_all_jobs",
                "share_nonmissing_descriptions",
            ),
            skills_rows,
        )
        write_csv(
            temporary / "salary.csv",
            (
                "year",
                "scope",
                "all_jobs",
                "valid_intervals",
                "invalid_or_missing",
                "p25",
                "median_midpoint",
                "p75",
            ),
            salaries,
        )
        write_json(
            temporary / "skill-evidence-local.json",
            {
                "restricted_local_review": True,
                "description": (
                    "只有词面和本机记录定位，无整行描述；复核需原始 CSV，不向仓库提交此文件。"
                ),
                "examples": evidence,
                "gold_labels": "未人工标注，不是准确率评测",
            },
        )
        plan_path = Path(__file__).with_name("curriculum-placeholder.json")
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        demand = {
            row["skill"]: row["share_all_jobs"]
            for row in skills_rows
            if row["year"] == min(inputs) and row["scope"] == "两市合计" and row["n"] > 0
        }
        write_json(
            temporary / "gap-example.json",
            {
                **curriculum_gap(plan, demand),
                "demand_evidence_mode": "historical",
                "demand_year": min(inputs),
            },
        )
        rules = {
            "skills": SKILLS,
            "provenance": "三个年度实际词面探查后人工选定；有限规则词表，不是标准技能词典",
            "patterns": {key: value.pattern for key, value in PATTERNS.items()},
            "counterexamples": [
                {
                    "label": "合成误判反例",
                    "text": "JavaScript和digital",
                    "naive_error": "Java/Git子串误报",
                    "accepted": [
                        h["skill"] for h in extract_skills("JavaScript和digital") if h["accepted"]
                    ],
                },
                {
                    "label": "合成否定反例",
                    "text": "无需Python；熟悉SQL",
                    "accepted": [
                        h["skill"] for h in extract_skills("无需Python；熟悉SQL") if h["accepted"]
                    ],
                },
                {
                    "label": "合成已知局限",
                    "text": "不熟悉Python也可培训",
                    "current_accepts": True,
                    "reason": "未识别所有否定；需人工判断要求与提及",
                },
            ],
        }
        write_json(temporary / "rules.json", rules)
        manifest = {
            "script_sha256": sha256(Path(__file__)),
            "curriculum_example_sha256": sha256(plan_path),
            "outputs": {p.name: sha256(p) for p in sorted(temporary.iterdir())},
        }
        write_json(temporary / "manifest.json", manifest)
        # Keep this standalone entry standard-library-only, including publication retries.
        for attempt in range(4):
            try:
                temporary.rename(output)
                break
            except PermissionError as error:
                if getattr(error, "winerror", None) not in {5, 32} or attempt == 3:
                    raise
                time.sleep(0.05 * (attempt + 1))
    except BaseException:
        shutil.rmtree(temporary)
        raise
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path(".local/data-audit/extract"))
    parser.add_argument(
        "--years", type=int, nargs="+", default=list(YEARS), choices=SUPPORTED_YEARS
    )
    parser.add_argument("--backtest", action="store_true", help="显式年度输入的2024/2025回顾性回测")
    parser.add_argument(
        "--matched-backtest", action="store_true", help="共同支持切片与误差分组；同时保留全年回测"
    )
    parser.add_argument(
        "--annual-input-dir", type=Path, help="2024/2025 CSV目录，默认同--input-dir"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = run(
            {
                year: (
                    args.annual_input_dir
                    if year in (2024, 2025) and args.annual_input_dir is not None
                    else args.input_dir
                )
                / f"上市公司招聘数据{year}.csv"
                for year in args.years
            },
            args.output,
            backtest=args.backtest,
            matched_backtest=args.matched_backtest,
        )
    except (ValueError, OSError, csv.Error) as error:
        parser.exit(
            2, f"分析失败：{error}\n请核对输入路径、UTF-8 CSV 和字段口径；使用新的输出目录。\n"
        )
    print(
        json.dumps(
            {
                "output": args.output.as_posix(),
                "selected_rows": {
                    year: row["selected_rows"] for year, row in summary["years"].items()
                },
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
