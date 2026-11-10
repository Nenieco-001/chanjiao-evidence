# 当前任务

本文件是唯一活动任务板。协调者为 root，revision 15。目标、研究口径、路线和偏移分别由 project.md、roadmap.md、status.md 维护。历史交接已做本机备份，原始数据与计算产物留在本机。

## F1 · 文档收敛

- 负责人为 root，状态为验收通过，revision 15。核心全局文档收敛为七份，20 份旧文档归档后移出活动目录，本轮核对的 41 个本地链接和锚点有效。
- 写范围为全局 Markdown、文档引用、AGENTS.md、README.md、CONTRIBUTING.md、CHANGELOG.md。
- 无前置依赖。核心全局文档保留项目说明、路线图、状态、任务板、数据契约、架构和开源引用。完成结果移至所属分析模块，重复留言、旧路线和交付草稿移出活动文档。
- 验收为一个目标口径、一个活动任务板、失效链接归零，偏移与学校/学生结果缺口写清，已有未提交内容可从本机备份恢复。

## F2 · 真实培养方案

- 负责人为 curriculum_researcher，状态为验收通过，revision 15。中财 2025 级公开方案课程切片已完成，本轮独立复核官方发布页、原文位置和十门课程数值。
- 写范围为 `data/curricula/official-cs-extract.json`；临时原文、提取与核验记录仅写 `.local/curriculum-research/`。
- 优先核对中央财经大学 2025 计算机科学与技术方案；若公开材料缺学时或不可访问，选择一所北京高校的完整公开方案，并说明选取理由。
- 只提取可核对的少量课程，保留学校、专业、版本、覆盖范围、原始来源、课程名/学分/学时/学期/先修与页码。材料缺失用 null，不推算或编造。技能标签需与课程内容证据区分。
- 验收为至少一个实际培养方案的课程切片可被 F3 接入，所有数值有官方原文位置，原文件仅在本机，不声称代表学校已批准的调整。

## F3 · 课程候选与约束

- 负责人为 curriculum_builder，状态为验收通过，revision 15。本轮独立运行 38 项课程测试通过，包含零增量仅归入基线的回归。全量回归的阻断单列于 F5。
- 写范围为 `src/chanjiao_evidence/curriculum.py`、`tests/test_curriculum.py`。
- 先按下方接口开发，F2 可并行。读取真实课程输入与独立情景配置，生成保持原方案及有限候选，检查课时/学分守恒、课程底线、先修与资源约束，保留不可行和无优势结果。
- 输出课程动作及理由、输入依据、约束检查、评价和修订记录。内容覆盖与学生结果分开；就业效果缺实证时返回明确缺项，不从招聘词频推算收益。
- 验收为真实课程格式、未知/缺失学时、非法动作、不可行约束、保持原方案、确定性及来源隔离有测试。不得扩平台、自动代入文献收益或改动既有需求分析。

## F4 · 正常入口与研究切片

- 负责人为 root，状态为验收通过，revision 15。新旧正常入口本轮均已运行，课程入口两次四产物逐字节一致，输入、源码和产物哈希核对通过。
- 写范围为 cli.py、对应 CLI 测试、情景样例和核心文档。
- 接入课程候选入口，基于真实课程和明确标记的决策假设运行至少一轮，输出可复核的动作、约束和效果证据缺口。
- 验收为旧入口回归通过，新入口得到具体课程动作与未识别效果状态，清楚区分已公开事实、情景假设、待教师审核项。

## F5 · 独立验收

- 原验收负责人为 realignment_verifier，本轮由 root 续做复验，状态为验收通过，revision 15。F1–F5 全部 PASS，当前课程切片与文档收敛变更可提交。
- 本轮证据独占 `.local/f5-resume-20261110-02/`。先前独立证据和启动失败日志分别保留在 `.local/realignment-verification/` 与 `.local/f5-resume-20261110-01/`。本轮公开文件修改范围仅为本任务板。
- 核对文档数量、链接、研究口径、原始来源和课程数值，跑全量测试/静态检查/构建/新旧 CLI 与两次确定性。无原始记录、凭据和受限文件进入公开 diff。

### 2026-11-10 最终复验摘要

分支为 `feat/project-realignment`，HEAD 为 `c562e0c979dfac987072fe54fbf4549b07ef220e`。本轮保留全部既有未提交修改。验收依据为本轮实际输出，历史成功记录分别保存。

- F1 PASS。docs 内七份核心文档、唯一活动任务板及 41 个本地链接和锚点已核对。29 项备份的字节数与 SHA-256 全部吻合，20 份移出文档可恢复。迁移的需求分析结果只改变引用与历史状态说明，原有数值和解释范围保留。
- F2 PASS。官网发布页为 2025 级，发布日期为 2025-09-02。官方六页 PDF 的第 5 页与 JSON 中十门课程的代码、名称、学分、总学时和学期逐项吻合，合计 24 学分、384 学时。本机原文哈希与 JSON 登记值一致，十门未公开先修关系均保留缺项标识。
- F3 PASS。课程模块 38 项测试通过，真实输入的核心计算两次一致。16 学时候选把专业综合实践从 32 学时/2 学分改为 48 学时/3 学分，把云计算与大数据技术从 48 学时/3 学分改为 32 学时/2 学分。32 学时候选保留为不可行，总学分学时守恒，默认选择原方案，学生掌握和就业效果保持未识别。
- F4 PASS。课程正常入口两次成功，四产物逐字节一致，清单中的实际输入字节、全部源码和三个结果哈希吻合。旧 run 合成基线两次四产物也一致，warehouse 的合成单行入库、限量汇总及 Parquet 导出通过。
- F5 PASS。全量 215 项测试、Ruff 两项、标准隔离构建及正常 CLI 通过。130 项入口与反例探针、45 项文档和原文核对、24 项哈希与打包检查通过，`git diff --check` 通过。原方案、未知输入、零增量、不可行候选、失败清理和拒绝覆盖均有实际检查。

### 实际命令与输出

下述命令使用项目 `.venv/Scripts/python.exe`。临时目录均位于本轮独占目录，完整入口参数、退出码和输出保存在 verify.py、对应 stdout/stderr 日志及各检查 JSON 中。

- `-m pytest -q -p no:cacheprovider --basetemp .local/f5-resume-20261110-02/pytest-tmp` 退出 0，215 passed in 18.03s。
- `-m ruff check . --no-cache` 退出 0，All checks passed；`-m ruff format --check . --no-cache` 退出 0，44 files already formatted。
- 在公共文件快照 source-snapshot 内执行 `-m build --outdir <本轮目录>/dist`，退出 0，正常隔离构建生成 0.4.0 sdist 与 wheel。任务板更新后同步快照并以 dist-final 新路径重建，再核对包内任务板与当前文件一致。
- `-m chanjiao_evidence curriculum --plan data/curricula/official-cs-extract.json --scenario data/examples/curriculum-scenario.json --output <本轮目录>/curriculum-a` 退出 0，curriculum-b 第二次同样成功。
- `-m chanjiao_evidence run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --evidence data/evidence/internships.json --output <本轮目录>/old-run` 退出 0，old-run-b 第二次同样成功。该示例明确标为 synthetic。
- `warehouse ingest`、`warehouse summary --limit 5`、`warehouse export` 均退出 0。输入仅为一条独立合成招聘记录，导出行数与内容哈希吻合，汇总未带出职位描述哨兵。
- verify.py 退出 0，130 项通过。audit.py 使用本机 Python 3.12 核对 PDF 和公开文件，45 项通过。final-checks.py 退出 0，24 项通过。新旧入口各四产物的完整 SHA-256 与构建包哈希保存在 final-checks.json。

### 公开范围与未验证项

核对既有跟踪文件 diff 和所有未跟踪、未忽略文件后，公开新增数据只有官方课程切片与独立情景 JSON。原始招聘记录、PDF、邮件、数据库和本机证据目录未进入公开变更，凭据模式检查无命中。sdist 包含公开输入、课程模块与分析结果，wheel 的全部模块字节与当前源码吻合，两个包均无受限路径和文件。

先前 `_ctypes` 与 Ruff 的启动失败本轮未复现。环境恢复的具体原因尚未定位，本轮没有修改业务代码或系统配置。当前通过结论依据此次完整运行，早先失败日志继续保留。

本轮未发现必须修复的业务代码问题。可提交结论覆盖首个真实课程切片、范围内候选与约束计算及文档收敛。完整培养规则、资源核定、历史效应迁移及学生结果证据仍为路线图中的研究工作。Python 3.11/3.12 全量兼容性、本机之外的新环境复现及完整比赛数据运行未在本轮验收。

## 接口与历史状态

输入、状态和产物统一见[数据契约](data-contract.md)。先前数据仓库、需求分析和材料任务已留在Git历史与本机备份中。已有材料的当前状态见status.md，后续领取只使用本任务板。
