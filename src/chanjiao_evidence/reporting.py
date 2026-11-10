"""Render an offline Chinese report from the pipeline's normalized report dictionary."""

import html
import re
from urllib.parse import quote, urlsplit

_NAMES = {
    "employment_rate": "就业率",
    "supervised_internship": "有指导的企业实习",
    "foundation": "基础课程",
    "specialty": "专业课程",
    "internship": "企业实习",
}
_ASSUMPTIONS = {
    "parallel untreated trends": "未改革时，处理组与对照组应有平行趋势",
    "no anticipation or spillovers": "无提前反应，组间无改革溢出",
    "stable outcome definition and population composition": "指标定义与人群构成稳定",
    "independent units, common adoption date, equal unit weights": (
        "单位相互独立，在同一年改革，按单位等权"
    ),
}
_CARD_LABELS = {
    "evidence_id": "证据编号",
    "authors": "作者",
    "year": "发表年份",
    "publication": "发表来源",
    "doi": "DOI",
    "source_version": "材料版本",
    "population": "研究人群",
    "action": "研究措施",
    "outcomes": "研究结果指标",
    "design": "研究设计",
    "assumptions": "识别假设",
    "transfer_limits": "外推边界",
    "reusable": "可借鉴方法",
    "related_work": "版本与相关研究",
    "data_status": "数据取得状态",
    "reported_results": "论文报告结果",
    "source_locations": "原文定位",
    "data_access": "数据取得路径",
    "status": "取得状态",
    "materials_obtained": "已取得材料",
    "microdata_acquired": "已取得微观数据",
    "public_download_verified": "已核验公开下载",
    "access_routes": "申请入口",
    "next_step": "下一步",
    "instruction": "取得说明",
    "label": "名称",
    "url": "链接",
    "location": "原文位置",
    "version": "版本",
}


def _name(value: str) -> str:
    return f"{_NAMES[value]}（{value}）" if value in _NAMES else value


def _plain_action_name(value: str) -> str:
    return _NAMES.get(value, "培养改革")


def _pp(value: float) -> str:
    return f"{0.0 if abs(value) < 1e-12 else value * 100:.2f} 个百分点"


def _interval(effect: dict) -> str:
    return f"{_pp(effect['ci95'][0])} 至 {_pp(effect['ci95'][1])}"


def _describe(value) -> str:
    if isinstance(value, dict):
        return "，".join(
            f"{_CARD_LABELS.get(key, key)} {_describe(item)}" for key, item in value.items()
        )
    if isinstance(value, list):
        return "，".join(_describe(item) for item in value)
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)


def _card_tables(card: dict) -> list[tuple]:
    tables = [
        (
            ["项目", "原文与核验记录"],
            [
                [_CARD_LABELS.get(key, key), _describe(value)]
                for key, value in card.items()
                if key
                not in {
                    "title",
                    "summary",
                    "source_url",
                    "matches_target_outcome",
                    "reported_results",
                    "source_locations",
                    "data_access",
                }
            ],
        )
    ]
    if card.get("reported_results"):
        tables.append(
            (
                ["论文结果指标", "报告值与原始单位", "原文解释", "原文定位"],
                [
                    [
                        f"{row['label']}（{row['outcome_id']}）",
                        (
                            f"{_describe(row['value'])} {row['unit']}"
                            if "value" in row
                            else "未从原文提取数值"
                        ),
                        row["interpretation"],
                        row["source_location"],
                    ]
                    for row in card["reported_results"]
                ],
            )
        )
    if card.get("source_locations"):
        tables.append(
            (
                ["原文材料", "原文定位", "版本", "来源链接"],
                [
                    [row["label"], row["location"], row["version"], row["url"]]
                    for row in card["source_locations"]
                ],
            )
        )
    if card.get("data_access"):
        tables.append(
            (
                ["数据取得", "当前记录"],
                [
                    [_CARD_LABELS.get(key, key), _describe(value)]
                    for key, value in card["data_access"].items()
                ],
            )
        )
    return tables


def _safe_url(value: str) -> bool:
    """Only make external source text clickable when it is an ordinary web URL."""
    if any(character.isspace() or ord(character) < 32 for character in value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def _markdown_text(value) -> str:
    escaped = html.escape(str(value), quote=False).replace("\n", " ").replace("\r", " ")
    return re.sub(r"([\\`*[\]{}|#()])", r"\\\1", escaped)


def _summary(report: dict) -> tuple[str, str]:
    effect = report["analysis"]["main"]
    estimate = effect["estimate"]
    direction = "零效应" if abs(estimate) < 1e-12 else "正效应" if estimate > 0 else "负效应"
    planning = report["planning"]
    selected = planning["selected_plan"]
    decision = (
        f"当前判据保持原方案 {selected}。"
        if selected == planning["baseline_plan_id"]
        else f"当前判据选中改革方案 {selected}。"
    )
    if report["metadata"]["evidence_mode"] == "synthetic":
        mode = "合成演示 · 检查实现与方案比较"
        scope = "合成数据只验证实现。真实学校的改革效果需要历史材料支持。"
    else:
        mode = "历史数据 · 结论以识别假设为条件"
        scope = "估计只说明这批单位与本次改革。推广到其他学校需要重新核对人群与执行条件。"
    return mode, f"点估计呈{direction}，双重差分为 {_pp(estimate)}。{decision}{scope}"


def _sections(report: dict) -> list[dict]:
    """Prepare shared readable content before applying format-specific escaping."""
    metadata = report["metadata"]
    analysis = report["analysis"]
    main = analysis["main"]
    planning = report["planning"]
    constraints = planning["constraints"]
    placebo = analysis["placebo"]
    sections = [
        {
            "title": "1 · 本次研究回答什么",
            "paragraphs": [
                "双重差分（DiD）从处理组的前后变化中扣除对照组的前后变化。"
                "估计对象是处理组平均处理效应（ATT），各单位等权。",
                "效应用比例差值计算，0.01 = 1 个百分点。表中的组均值以百分比显示。",
            ],
            "tables": [
                (
                    ["项目", "本次输入"],
                    [
                        ["措施", _name(metadata["action_id"])],
                        ["结果指标", _name(metadata["outcome_id"])],
                        ["结果时间窗", metadata["outcome_window"]],
                        ["人群", metadata["population"]],
                        ["改革年份", metadata["adoption_year"]],
                        ["主比较年份", f"{main['before_year']} → {main['after_year']}"],
                        [
                            "处理组 / 对照组单位数",
                            f"{main['treated_units']} / {main['control_units']}",
                        ],
                        ["数据许可", metadata["data_license"]],
                    ],
                )
            ],
            "links": [(source["title"], source["url"]) for source in metadata["sources"]],
        },
        {
            "title": "2 · 改革前后发生了什么",
            "paragraphs": [
                f"处理组变化 {_pp(main['treated_change'])}，对照组变化 "
                f"{_pp(main['control_change'])}，扣除后为 {_pp(main['estimate'])}。",
                f"95% 置信区间为 {_interval(main)}。区间采用 HC3 稳健协方差和 t 分布近似。"
                "样本少时区间精度受限，区间计算仍依赖识别假设。",
            ],
            "tables": [
                (
                    ["年份", "处理组均值", "对照组均值"],
                    [
                        [row["year"], f"{row['treated_mean']:.2%}", f"{row['control_mean']:.2%}"]
                        for row in report["trajectory"]
                    ],
                )
            ],
        },
        {
            "title": "3 · 诊断与识别假设",
            "paragraphs": [
                f"伪改革把 {placebo['before_year']} → {placebo['after_year']} 当作改革窗口，"
                f"估计为 {_pp(placebo['estimate'])}，95% 区间为 {_interval(placebo)}。"
                "两期改革前数据只检查这一段的差异趋势，需补更长的改革前记录。",
                "逐单位删除每次剔除一个单位后重估，检查结论是否依赖某个学校或专业。",
                f"使主点估计归零的差异趋势幅度为 "
                f"{_pp(analysis['bias_to_erase_point_estimate'])}，按点估计绝对值计算。",
                "识别假设包括 "
                + "，".join(_ASSUMPTIONS.get(value, value) for value in analysis["assumptions"])
                + "。",
            ],
            "tables": [
                (
                    ["删除的单位", "重估效应"],
                    [
                        [row["excluded_unit"], _pp(row["estimate"])]
                        for row in analysis["leave_one_unit_out"]
                    ],
                )
            ],
        },
        {
            "title": "4 · 两个方案怎样调整课程",
            "paragraphs": [
                f"基线为 {planning['baseline_plan_id']}，本次选中 {planning['selected_plan']}。"
                "仅在方案可行且保守增量大于零时选择改革，收益相同选择成本较低的方案。",
                "成本采用输入中的成本单位。真实方案需补单位、计价周期和测算依据。",
            ],
            "tables": [
                (
                    ["方案", "成本", "可行性", "违规项", "保守增量"],
                    [
                        [
                            row["plan_id"],
                            f"{row['cost']:g}",
                            "可行" if row["feasible"] else "不可行",
                            "，".join(row["violations"]) or "无",
                            _pp(row["conservative_gain"]),
                        ]
                        for row in planning["plans"]
                    ],
                ),
                (
                    ["模块", "原方案学分", "改革方案学分", "学分变化"],
                    [
                        [
                            _name(row["module"]),
                            row["baseline"],
                            row["candidate"],
                            f"{row['delta']:+d}",
                        ]
                        for row in planning["credit_changes"]
                    ],
                ),
                (
                    ["资源约束", "输入限值"],
                    [
                        ["总学分", constraints["total_credits"]],
                        ["成本预算", f"{constraints['budget']:g}"],
                    ]
                    + [
                        [f"{_name(key)}最低学分", value]
                        for key, value in constraints["minimum_credits"].items()
                    ]
                    + [
                        [f"{_name(key)}最高学分", value]
                        for key, value in constraints["maximum_credits"].items()
                    ],
                ),
            ],
        },
        {
            "title": "5 · 换一组假设，方案会不会改变",
            "paragraphs": [
                "迁移系数表示历史效应带到当前方案的比例。偏差预算表示对未观测偏差和迁移误差的扣减。"
                "两者都是分析假设，取值依据需用外部材料补齐。",
                "每格保守增量 = 迁移系数 × 95% 区间下界 − 偏差预算。"
                "主方案比较取输入迁移系数中最小的保守增量。下表每行单独固定一组假设。",
                f"主比较采用的偏差预算为 {_pp(planning['bias_budget_assumption'])}。",
            ],
            "tables": [
                (
                    ["迁移系数假设", "偏差预算假设", "改革保守增量", "该格选中方案"],
                    [
                        [
                            f"{row['transfer_factor_assumption']:.2f}",
                            _pp(row["bias_budget_assumption"]),
                            _pp(row["conservative_gain"]),
                            row["selected_plan"],
                        ]
                        for row in planning["sensitivity"]
                    ],
                )
            ],
        },
    ]
    evidence = report["evidence"]
    sections.append(
        {
            "title": "6 · 真实论文提供了什么依据",
            "paragraphs": [
                "文献用于交代研究方法、结果指标与外推范围。"
                f"used_for_estimation={str(evidence['used_for_estimation']).lower()}。"
                "本次数值估计来自输入面板，方案收益来自该估计及敏感性假设。"
            ],
        }
    )
    if not evidence["cards"]:
        sections[-1]["paragraphs"].append(
            "未提供论文证据。请补可定位的论文原文、研究设计、结果指标、外推边界和数据取得状态。"
        )
    for index, card in enumerate(evidence["cards"], 1):
        match = "目标指标匹配" if card["matches_target_outcome"] else "目标指标不匹配"
        sections.append(
            {
                "title": f"论文 {index} · {card['title']}",
                "paragraphs": [f"{match}。当前目标为 {metadata['outcome_id']}。"]
                + ([card["summary"]] if card.get("summary") else []),
                "tables": _card_tables(card),
                "links": [("论文原文", card["source_url"])],
            }
        )
    sections.append(
        {
            "title": "7 · 缺什么材料，下一步补什么",
            "paragraphs": list(report["limitations"])
            + [
                "补学校历版培养方案、覆盖年级与实际执行年份、实习时长与质量要求、同期改革清单，"
                "用于核对措施与识别假设。",
                "补处理组和对照组更长的改革前结果、毕业后同一时间窗的就业记录及指标说明，"
                "用于检查趋势和统计口径。按授权提供去标识、可用的汇总数据。",
                "补实习岗位容量、课程替代损失、师资和成本测算材料，"
                "再为迁移系数与偏差预算给出取值依据。",
                "任务输出正确、合成仿真内部一致、预测准确与真实培养效果分别评价。"
                "本报告未开展留出学校的预测回测，学校就业率也不能替代学生能力测量。",
            ],
        }
    )
    return sections


_STYLE = """
:root {
  --ink: #1f2a30; --muted: #657077; --paper: #f3efe7; --card: #fffdf9;
  --line: #e2dacd; --accent: #0f6b60; --accent-soft: #e7f1ee; --warm: #b7793b;
  --sans: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
  --serif: "Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", serif;
  color-scheme: light;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 40px 24px 64px; color: var(--ink);
  font-family: var(--sans); font-size: 16px; line-height: 1.8;
  background:
    radial-gradient(circle at 10% 0%, #fbf7ee 0, transparent 36%),
    linear-gradient(180deg, #f5f1e9 0%, #eceae3 100%);
}
main {
  max-width: 1080px; margin: 0 auto; overflow: hidden;
  background: var(--card); border: 1px solid var(--line); border-radius: 18px;
  box-shadow: 0 24px 70px rgba(42, 36, 24, .12);
}
header {
  padding: 46px 56px 34px; border-top: 6px solid var(--accent);
  background: linear-gradient(180deg, #fffdf8 0%, #fffdf9 60%, #fbf8f1 100%);
}
.eyebrow {
  display: flex; align-items: center; gap: 10px; margin: 0 0 18px;
  color: var(--accent); font-size: 12px; font-weight: 700;
  letter-spacing: .18em; text-transform: uppercase;
}
.eyebrow .dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--accent);
  box-shadow: 0 0 0 4px rgba(15, 107, 96, .12);
}
h1 {
  max-width: 100%; margin: 0 0 18px; font-family: var(--serif);
  font-size: 38px; font-weight: 700; line-height: 1.3; letter-spacing: -.02em;
  text-wrap: balance;
}
h2 {
  margin: 0 0 14px; font-family: var(--serif); font-size: 25px;
  font-weight: 700; line-height: 1.4; letter-spacing: -.01em;
}
section { padding: 30px 56px 34px; border-top: 1px solid var(--line); }
section:first-of-type { border-top: 0; }
p { margin: 10px 0; overflow-wrap: anywhere; }
.summary {
  margin: 0 0 24px; padding: 18px 20px; background: var(--accent-soft);
  border-left: 4px solid var(--accent); border-radius: 0 10px 10px 0;
  font-size: 17px; line-height: 1.8;
}
.metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 26px 0 22px; }
.metric {
  position: relative; min-height: 98px; padding: 16px 16px 14px;
  background: #fffefb; border: 1px solid var(--line); border-radius: 12px;
}
.metric span {
  display: block; margin-bottom: 6px; color: var(--muted);
  font-size: 12px; line-height: 1.5;
}
.metric strong {
  display: block; color: var(--ink); font-family: var(--serif);
  font-size: 28px; line-height: 1.1; font-variant-numeric: tabular-nums;
}
.metric::after {
  content: ""; position: absolute; left: 16px; bottom: 0; width: 28px;
  height: 3px; background: var(--accent); border-radius: 3px 3px 0 0;
}
.effect {
  display: inline-flex; align-items: baseline; gap: 10px; margin: 2px 0 0;
  padding: 12px 16px; background: #fff; border: 1px solid var(--line);
  border-radius: 999px; font-size: 15px;
}
.effect-label {
  padding: 3px 8px; border-radius: 999px; background: var(--accent-soft);
  color: var(--accent); font-size: 11px; font-weight: 800; letter-spacing: .12em;
}
.table-wrap {
  overflow-x: auto; margin: 18px 0;
  border: 1px solid var(--line); border-radius: 12px;
}
table { width: 100%; border-collapse: collapse; background: #fffefb; font-size: 14px; }
th, td {
  padding: 11px 14px; border-bottom: 1px solid #eee7db; text-align: left;
  vertical-align: top; overflow-wrap: anywhere;
}
th {
  background: #f6f1e7; color: #4d5b60; font-size: 12px;
  font-weight: 800; letter-spacing: .06em; text-transform: uppercase;
}
tr:last-child td { border-bottom: 0; }
tbody tr:nth-child(even) { background: #fcfaf5; }
tbody tr:hover { background: #f7f2e8; }
td { font-variant-numeric: tabular-nums; }
a {
  color: #0b6373; text-decoration-thickness: 1px;
  text-underline-offset: 3px; overflow-wrap: anywhere;
}
a:hover { color: var(--accent); }
.source { color: var(--muted); font-size: 12.5px; }
footer {
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: 16px;
  padding: 22px 56px 28px; border-top: 1px solid var(--line);
  background: #fbf8f1; color: var(--muted); font-size: 12px;
}
.footer-mark { color: var(--accent); font-family: var(--serif); }
@media (max-width: 760px) {
  body { padding: 0; background: var(--card); }
  main { border: 0; border-radius: 0; box-shadow: none; }
  header, section { padding-left: 22px; padding-right: 22px; }
  header { padding-top: 32px; }
  h1 { font-size: 31px; }
  .metrics { grid-template-columns: repeat(2, 1fr); }
  footer { padding: 18px 22px; }
}
@media print {
  @page { margin: 16mm; }
  body { background: #fff; padding: 0; font-size: 10pt; }
  main { max-width: none; border: 0; border-radius: 0; box-shadow: none; }
  header { padding: 0 0 18px; border-top: 0; background: none; }
  section { padding: 18px 0; }
  h1 { font-size: 24pt; }
  h2 { font-size: 15pt; break-after: avoid; }
  .metrics { grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .metric { min-height: auto; padding: 10px; border-color: #ddd; }
  .metric strong { font-size: 16pt; }
  .metric::after { display: none; }
  .summary { background: #f4f4f4; border-left-color: #666; }
  .table-wrap { overflow: visible; border: 0; border-radius: 0; }
  table { font-size: 8.8pt; }
  th { background: #f1f1f1; color: #000; }
  a { color: inherit; text-decoration: none; }
  footer { margin-top: 22px; padding: 12px 0 0; border-top: 1px solid #ccc; background: none; }
}
"""


def render_html(report: dict) -> str:
    """Return a self-contained, printable HTML report with escaped source text."""
    mode, summary = _summary(report)
    main = report["analysis"]["main"]
    trajectory = {row["year"]: row for row in report["trajectory"]}
    metrics = [
        (f"处理组 · {main['before_year']}", trajectory[main["before_year"]]["treated_mean"]),
        (f"处理组 · {main['after_year']}", trajectory[main["after_year"]]["treated_mean"]),
        (f"对照组 · {main['before_year']}", trajectory[main["before_year"]]["control_mean"]),
        (f"对照组 · {main['after_year']}", trajectory[main["after_year"]]["control_mean"]),
    ]
    parts = [
        '<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>产教智对 · 改革证据与方案比较</title><style>{_STYLE}</style></head>",
        f'<body><main><header><p class="eyebrow"><span class="dot"></span>{html.escape(mode)}</p>',
        f"<h1>{html.escape(_plain_action_name(report['metadata']['action_id']))}，值得调整培养方案吗？</h1>",
        f'<p class="summary">{html.escape(summary)}</p><div class="metrics">',
    ]
    parts.extend(
        f'<div class="metric"><span>{html.escape(label)}</span><strong>{value:.2%}</strong></div>'
        for label, value in metrics
    )
    parts.append(
        f'</div><div class="effect"><span class="effect-label">DiD</span>'
        f"<strong>{_pp(main['estimate'])}</strong>"
        f"<span>95% 置信区间 {_interval(main)}</span></div></header>"
    )
    for section in _sections(report):
        parts.append(f"<section><h2>{html.escape(section['title'])}</h2>")
        parts.extend(f"<p>{html.escape(text)}</p>" for text in section.get("paragraphs", []))
        for headers, rows in section.get("tables", []):
            parts.append('<div class="table-wrap"><table><thead><tr>')
            parts.extend(f'<th scope="col">{html.escape(str(value))}</th>' for value in headers)
            parts.append("</tr></thead><tbody>")
            for row in rows:
                parts.append(
                    "<tr>"
                    + "".join(f"<td>{html.escape(str(value))}</td>" for value in row)
                    + "</tr>"
                )
            parts.append("</tbody></table></div>")
        for label, url in section.get("links", []):
            content = f"{html.escape(label)} · {html.escape(url)}"
            if _safe_url(url):
                content = (
                    f'<a href="{html.escape(url, quote=True)}" rel="noopener noreferrer">'
                    f"{content}</a>"
                )
            parts.append(f'<p class="source">{content}</p>')
        parts.append("</section>")
    parts.append(
        '<footer><span class="footer-mark">产教智对 · 离线研究报告</span>'
        "<span>数值与来源以同目录 report.json 为准</span></footer>"
        "</main></body></html>\n"
    )
    return "\n".join(parts)


def render_markdown(report: dict) -> str:
    """Return the same report content with raw HTML and Markdown source text escaped."""
    mode, summary = _summary(report)
    parts = ["# 产教智对 · 改革证据与方案比较", _markdown_text(mode), _markdown_text(summary)]
    for section in _sections(report):
        parts.append(f"## {_markdown_text(section['title'])}")
        parts.extend(_markdown_text(text) for text in section.get("paragraphs", []))
        for headers, rows in section.get("tables", []):
            lines = ["| " + " | ".join(_markdown_text(value) for value in headers) + " |"]
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            lines.extend(
                "| " + " | ".join(_markdown_text(value) for value in row) + " |" for row in rows
            )
            parts.append("\n".join(lines))
        for label, url in section.get("links", []):
            if _safe_url(url):
                safe_url = quote(url, safe=":/?#@!$&'*+,;=%-._~")
                parts.append(f"[{_markdown_text(label)}]({safe_url})")
            else:
                parts.append(f"{_markdown_text(label)} · {_markdown_text(url)}")
    return "\n\n".join(parts) + "\n"
