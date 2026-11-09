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


def _analyse(year, path, evidence):
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


def retrospective_backtest(year_groups):
    """冻结的朴素基线；年份等权均值不按样本数加权，也不是因果估计。"""
    profiles = {year: _profile(group) for year, group in sorted(year_groups.items())}
    folds = []
    for target in (2024, 2025):
        train_years = [year for year in profiles if year < target]
        training = [profiles[year] for year in train_years]
        latest = training[-1]
        prediction = {}
        for field in ("families", "skills"):
            prediction[field] = {}
            for key in latest[field]:
                values = [p[field][key] for p in training if p[field][key] is not None]
                prediction[field][key] = statistics.mean(values) if values else None
        values = [p["salary_median"] for p in training if p["salary_median"] is not None]
        prediction["salary_median"] = statistics.mean(values) if values else None
        actual = profiles[target]
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


def run(inputs, output, *, backtest=False):
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
        annual_groups = {}
        for year, path in sorted(inputs.items()):
            sample, groups = _analyse(year, Path(path), evidence)
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
        temporary.rename(output)
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
