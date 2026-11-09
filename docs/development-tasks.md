# 正式开发任务板

本轮协调者为 root。任务版本为 revision 2，D1–D4 已于 2026-11-09 完成并通过独立验收。特性分支为 `feat/analysis-workbench`，基于已合并 PR #1 的 main。用户授权本轮验收后推送、创建 PR 和评论 `@codex review`，合并由用户执行。

## 本轮成果

沿用 `chanjiao run`，生成中文 `report.html`、`report.md` 和原有 JSON。报告串起改革估计、原方案对照、学分调整、资源约束、敏感性和真实论文依据。默认离线、无新增运行依赖。合成面板与真实文献分别标识，文献结果只作为背景证据，不自动转成当前学校的就业率收益。

## D1 · 论文证据核验

- 负责人为 evidence_curator，状态为完成，revision 2，验收通过。交付两张卡片、原文定位和数据入口。自测文献解析通过，微观数据尚未取得。
- 写范围为 `data/evidence/internships.json`、`docs/evidence-findings.md`。
- 无前置依赖。
- 核验现有两项研究的原始方法、结果、数据可获取性和外推范围，必要时补公开来源。至少两张真实卡片。无公开数据就记录具体申请入口或限制，不能拼造历史面板。
- 验收为每个结论有原始出处，收入、回邀、就业和能力分开，卡片通过 D3 入口解析。交付实际查阅链接与数据取得状态。

## D2 · 中文成果报告

- 负责人为 report_builder，状态为完成，revision 2，验收通过。定向测试 23 项通过，带实际文献入口已跑通。
- 写范围为 `src/chanjiao_evidence/reporting.py`、`tests/test_reporting.py`。
- 接口依赖下面的报告契约，研发可与 D3 并行。
- 输出 `render_html(report: dict) -> str` 和 `render_markdown(report: dict) -> str`。无外部资产、网络、JS 或新增依赖，HTML 可直接打开和打印。
- 验收包括正效应、零效应、负效应、无证据、论文指标不匹配和 HTML 注入文本，显示单位为百分点，保留原始指标和来源。

## D3 · 入口与分析整合

- 负责人为 root，状态为完成，revision 2，验收通过。完整测试 85 项通过，静态检查与格式检查通过，实际文献入口已生成四份产物。
- 写范围为 `pipeline.py`、`planning.py`、`cli.py`、新建 `evidence.py`，对应测试文件，及全部共享文档和配置。
- 依赖 D2 的渲染接口，D1 的卡片格式沿用旧版本。
- 新增可选 `--evidence`，原有调用保持兼容。解析和哈希共用输入字节。输出新增两份报告并纳入 manifest，继续拒绝覆盖和清理失败临时目录。
- 学分差异、资源限制和迁移系数 × 偏差预算的敏感性格点都由后端计算。临界偏差与伪改革、逐单位删除结果分开展示。
- 验收为正常入口生成四份产物、哈希一致、相同输入报告字节一致，既有测试通过，明确文献未参与估计。

## D4 · 独立验收

- 负责人为 workbench_verifier，状态为完成，revision 2，独立验收通过。
- 只读受控文件，独占 `.local/workbench-verification/` 写验收记录。
- 跑 pytest、ruff、format、build 和正常 CLI，独立复算正效应及零效应，复跑报告字节比较，核对链接、diff 与敏感信息，检查结论没有超出证据。逐项 PASS/FAIL，给出可提交或不可提交。
- 验收结果：85 项测试通过；离线构建、四份产物、哈希与确定性、文献隔离、HTML/Markdown 安全、独立复算均通过；首轮阻断的 Windows 发布瞬态失败与文档/版本定稿缺口已修复后复验。

## 报告接口

保留原有 `schema_version`、`metadata`、`analysis`、`planning`、`limitations`。

新增 `trajectory` 列表，每项为 `year`、`treated_mean`、`control_mean`，均为比例原值。新增 `evidence` 对象，含 `status`（not_provided 或 literature_context）、`used_for_estimation=false`、`cards`。每张卡片保留原始字段并增加 `matches_target_outcome` 布尔值。卡片原有字段见 `data/evidence/internships.json`。

`planning` 新增 `baseline_plan_id`、`constraints`（total_credits、minimum_credits、maximum_credits、budget）、`credit_changes` 列表（module、baseline、candidate、delta）、`sensitivity` 列表（transfer_factor_assumption、bias_budget_assumption、conservative_gain、selected_plan）。原有 plans 保留原顺序。敏感性每行固定一个 factor 和 bias，真实条件不明确时仅用于展示假设。

HTML 和 Markdown 由 D2 读取这些内部已规范化字段，不重复校验。外部文献卡片由 D3 在入口校验。没有文献时 cards 为空，报告写清该步骤缺输入。元数据可包含中文或不可信文本，渲染按外部文本转义并限制链接协议。
