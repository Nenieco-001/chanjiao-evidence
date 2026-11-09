# 需求侧工作台任务板

## 赛前执行材料（revision 10，C11）

- 编号与负责人：C11，Codex（文档实现者）；外部协调者负责独立验收、提交与 PR。
- 状态：完成，协调者验收通过；本 revision 只由本实现者串行写入，不重复认领 C1–C10。
- 写范围：新建 `docs/competition-qa.md`、`docs/competition-data-request.md`、
  `docs/competition-final-checklist.md`；本任务板新增 C11；`CHANGELOG.md` 追加一条索引。
  不修改其他文件，不执行任何 Git/gh 命令，不访问 D 盘原始数据，不扩平台。
- 前置依赖：C1–C10 的既有证据与协调者验收记录；本轮已读 README、研究规划、数据契约、
  赛题说明、报告草稿、答辩大纲、需求分析、工作台 README、任务板与 CHANGELOG。
  第 6 批 PPTX/DOCX/PDF 初稿状态来自本轮人类交接，本机目录拒绝访问，未作渲染验收。
- 验收标准：15–20 问逐题包含结论、2–3 句证据、禁说边界和追问所需材料；
  七组供给数据申请逐组列字段、用途、最小样本、责任角色、验收和替代；
  四交付物与五维评分逐项列状态、路径、负责人、验收和风险。
  校验新增链接及锚点，保留全部旧任务/变更条目；无真实学校课程或就业预测。
- C11-R（revision 10）：`c11_reader` 文档读者复核者，读者自查完成，PASS；前置三份文档已起草。
  写范围：无，只读本批三文档与其引用的仓库文档；不运行分析、不访问受限产物或 D 盘。
  验收：逐项检查覆盖、结论边界、数字、字段、可执行步骤与潜在歧义；只回报问题，不替协调者验收。

### C11 自查与交接（2026-11-10）

- 改了什么：新增问答卡、供给数据申请单、最终检查表；本任务板登记 C11；CHANGELOG 追加索引。
  问答覆盖 20 问；申请覆盖 7 组、21 个字段包；检查覆盖 4 交付物及 5 评分维度。
- 为什么：把现有证据变成可直接用于追问、申请补件和提交验收的材料，明确谁补什么、缺失时停止哪一步。
- 怎么验证：PowerShell 设置 UTF-8 管道，标准库脚本经 `python -` 检查本地 Markdown 链接与章节锚点、
  问答四栏及证据句数、申请组与编号、四交付物/五维评分字段、围栏/行尾空白和常见凭据模式；
  对照已读分析正文核对 20 项关键文本数字与两项覆盖率；以编辑前文本比对旧任务/变更条目完整保留。
- 输出：文档检查退出 0；88 处本地链接、其中 48 处章节锚点有效；20 问各有 2–3 句证据，
  7 组/21 包及 4+5 项结构齐全；关键来源与 39/3,560、597/3,272 覆盖率吻合。
  原任务与原 CHANGELOG 条目完整保留；本批未发现常见凭据/私钥/邮箱模式。
- 读者复核：C11-R 无必须修复项，判定文档自查 PASS、整包仍不可提交；
- 协调者验收（2026-11-10）：73 处本地链接 0 缺失，三份材料数字与既有报告一致，C11 通过；整包仍因真实供给/学生结果/许可/视频成片不可提交。
  建议 Q06 明确重叠分母是目标发布记录，已由实现者采纳，避免转述为企业数或确认转发数。
- 未完成与验证边界：本机 `artifacts/competition-deliverables-regen/` 访问被拒，
  PPTX/DOCX/PDF 仅按人类交接登记为初稿、未入 Git，未核准确文件名、页数、哈希或渲染。
  真实供给、学生结果、许可/平台说明、独立评价、视频成片及四件材料最终验收仍缺。
  本批只写 Markdown，未重跑分析、pytest、Ruff、build 或正常 CLI，未核外部链接。
  全程未执行 Git/gh，未访问 D 盘原始数据；协调者负责最终验收、提交与 PR。

## 第 5 批：参赛交付物骨架（revision 9）

- C10，Codex（文档实现者），完成，协调者验收通过；外部协调者负责提交与 PR。
  写范围：新建 `docs/competition-report-draft.md`、`docs/competition-defense-outline.md`；
  本任务板新增本批记录；`CHANGELOG.md` 仅追加交付物条目。其他文件不写。
  前置：C1–C9 已由协调者验收；读取赛题说明、分析报告、工作台 README、旧任务板、
  变更记录及本机 outputs/review_package 的研究方案和验证补充。
  步骤：登记已验收数字和限制；按四任务起草报告，按评审五维度组织答辩与视频；
  核对引用数字、链接、示例标识及本批文档增量，交协调者验收。
  验收：报告覆盖三维差距、课程/方向/招生模板、验证失败条件和至少三个风险；
  答辩含 10–12 页逐页内容及五分钟六段脚本；无虚构学校课程、就业收益或因果结论。
  限制：只写工作区文档，不执行任何 Git 或 gh 命令，不访问 D 盘原始数据，不扩平台。

### C10 自查与交接（2026-11-10）

- 协调者验收：两份文档 21 个本地链接有效，数字与已验证报告一致；C10 通过。

- 改了什么：新增四任务报告骨架、12 页逐页答辩大纲与六段视频脚本；
  本任务板新增 C10；CHANGELOG 仅追加一条带链接的交付物说明。
- 为什么：把已验收的需求侧分析组织成参赛材料，同时明确真实供给、学校决策和效果证据的缺口。
  不搬用旧 Demo 的模拟课程、代理分或文献效应；现有课程 JSON 只作为 synthetic 接口示例。
- 怎么验证：PowerShell 设置 UTF-8 管道后，以 here-string 经 `python -` 执行标准库文档自查，
  核对数字词元、八组折/方法指标、样本/覆盖分母、课程 JSON、页数、脚本时长和本地链接；
  对比编辑前读取的 TASKS/CHANGELOG 文本，检查旧记录保留。没有调用 Git 查看差异。
- 输出：文档自查退出 0；八组回测指标与三年度/共同支持样本吻合；课程 JSON 与原占位文件相等；
  21 个本地 Markdown 文件链接存在；四任务、12 页逐页字段、连续六段合计 300 秒检查通过；
  代码围栏与行尾空白检查通过；新文档和 CHANGELOG 未命中常见凭据/私钥/邮箱模式。
  原任务记录与原 CHANGELOG 条目保留。以上仅为本批文档自查，不能代替协调者验收。
- 验证边界：本批数字依据 `docs/competition-analysis.md` 与既有协调者验收记录；
  尝试列出本机 verified-final-01、verified-backtest-01、verified-matched-final-01 时均被拒绝访问，
  因此没有重新读取聚合产物、复算原始记录或重跑分析；不宣称本批重现了既有运行。
  仅修改 Markdown，未重跑 pytest、Ruff、build 或正常 CLI，不把旧批次通过当作本批新运行。
- 未完成：真实学校培养方案、大纲、学分/学时、学生结果、方向/招生与资源材料；
  平台说明、许可与独立标签；学校候选、情景参数、冻结评价及四年效果均未形成结果。
  PDF、实际 PPT、视频与图形渲染/录音计时尚未制作或验收；外部链接未重新访问。
  本轮没有执行任何 Git/gh 命令，也未读取或修改 D 盘原始数据。协调者负责独立验收与提交/PR。

## 第 4 批：共同支持与泄漏检查（revision 8）

本批实施计划使用 writing-plans 技能，沿用本任务板。负责人 Codex（实现者），
外部协调者负责独立验收与提交；本轮不执行 add/commit/push/gh，不修改 src、数据或数据库。
下列任务串行执行，写范围只由本实现者写入；旧批次验收记录保留。
协调者独立验收：173 passed、ruff/format 通过；可比切片正式产物为 verified-matched-final-01/02。

- C7，Codex，完成，协调者验收通过。写范围：`workbench.py`、`tests/test_competition_analysis.py`。
  前置：指定文档、模块及调用方已读，分支/HEAD 核对一致，工作区干净。
  步骤：先补无共同支持、平台缺失、空组、联合支持与稳定性失败用例；
  实现可选匹配模式，逐层与完整组合均要求所有训练年和目标年共同支持；
  保留全年对照和两种方法，输出五维误差组与跨年重复风险；再跑对应测试。
  验收：断层停止评分、缺失不算共同平台；分母、覆盖、零命中、小样本、无优势均保留。
- C8，Codex，完成，协调者验收通过（Codex 环境 Ruff 阻断；协调者正常环境通过）。写范围：Git 忽略的 `artifacts/competition-analysis/`、
  `.local/competition-batch4/`。前置 C7。
  步骤：实际运行到两个新目录，逐文件比较字节和 manifest；全仓 pytest、Ruff、
  format、build、正常 CLI；核对输入哈希、指标与失败情况，不覆盖旧目录。
  验收：至少 163 项全过；运行证据如实记录，环境失败不算通过。
- C9，Codex，完成，协调者验收通过。写范围：本文件、`README.md`、`docs/competition-analysis.md`、
  `CHANGELOG.md`。前置 C8。
  步骤：定稿共同支持口径、实际样本和误差、泄漏与不可下的结论、复现命令及未完成项；
  检查链接、diff 与敏感内容。
  验收：报告数字来自实际产物，无因果外推，交接已由协调者验收。

## 第 2/3 批历史记录

revision 6；本批实现者 Codex，提交与 PR 的协调者仍为人类指定的外部协调者。
协调者独立验收：163 passed、ruff/format 通过；正式产物为 verified-final-01/02 与 verified-backtest-01/02。
所有任务由本实现者串行执行，不认领已有 W1–W4，不修改共享配置或现有 src 模块。
本批按人类明确授权补充 CHANGELOG 草稿，由协调者最终定稿；不执行 Git 写入或远端操作。

- C5，Codex，完成，协调者验收通过。写范围：C1–C3 文件及 `CHANGELOG.md` 草稿。
  前置：第 2 批协调者已反馈三处 E501 和 Ruff 格式差异。
  验收：仅格式阶段全仓仍 157 passed；verified-final-01/verified-final-02 的 11 文件逐字节一致；
  与原正式产物比较除脚本哈希外不改变内容；保留 Ruff 环境限制。
- C6，Codex，完成，协调者验收通过。写范围：`analysis/competition/`、对应测试、分析报告、
  Git 忽略的 `.local/analysis-data/` 与 `artifacts/competition-analysis/`。
  前置 C5。只读提取 2024/2025，核验年度语义后显式映射；最小回顾性基线回测配测试，
  写明样本、误差、覆盖率、空样本与限制。无法执行则记录具体阻断，不编造数字。

- C1，Codex，完成，协调者验收通过。写范围：`analysis/competition/`、新增
  `tests/test_competition_analysis.py` 及 `MANIFEST.in` 的一行分析目录打包清单。
  追加清单是为避免 sdist 携带新增测试、却遗漏被测分析脚本及占位输入；不改运行依赖。
  前置：赛题、质量评估、仓库说明及本地研究方案已读。
  验收：标准库流式分析；明确分年口径；规则、分母、去重、缺失、薪资与失败清理有测试。
- C2，Codex，完成，协调者验收通过。写范围：Git 忽略的 `artifacts/competition-analysis/`。
  前置 C1。验收：实际运行三个已有年度 CSV，输出聚合 CSV/JSON/SVG、哈希、样本量、
  缺失率和本机技能证据，不读取其他原包或数据库；两次运行逐文件字节相同。
- C3，Codex，完成，协调者验收通过。写范围：`docs/competition-analysis.md`。
  前置 C2。验收：边界、实际数值、2024–2025 回测及 2026 留出污染说明、
  示例供给 schema 和差距接口、命令及未完成项清楚。
- C4，外部协调者/其指定验证者，完成，协调者验收通过。只读最终代码、测试和文档；
  独占输出目录由验证者指定。前置 C1–C3 已通过。
  验收：独立复算、全量测试、ruff、format、build、正常 CLI、确定性、
  链接与敏感内容检查。实现者的自测不能代替独立验收。

共享文件 `CHANGELOG.md` 本批按人类授权追加草稿，协调者定稿；`.gitignore` 不改。
本实现者不执行 Git 写入。本批 C5/C6 的自测证据附后，C4 的最终独立验收仍由协调者处理。

## 第 2 批初次交接：2026-11-10（历史记录）

本节保留初次交接的命令、结果及当时未完成项；当前状态以文末 revision 6 补充交接为准。

交付 8 个工作区文件：本目录五个文件、`tests/test_competition_analysis.py`、
`docs/competition-analysis.md`、`MANIFEST.in`。只在后者追加一行，确保 sdist
同时带分析脚本、占位输入和相应测试。没有修改现有 src、依赖、CHANGELOG 和 Git 忽略规则。

正式复核产物为 `artifacts/competition-analysis/verified-final-01/` 和 `verified-final-02/`；
旧的 final-01/02 目录受本机 Windows 权限限制为空，不参与复核。
每套 11 个文件（CSV/JSON/SVG/manifest），另有根目录 `verification.json` 保存自检结果。
中间 `run-01/` 保留为探索记录，不当作最终脚本版本的复核目录。

### 命令与输出

标准库分析两次均退出 0，终端输出各年 `selected_rows` 为 12678、4035、286：

```powershell
python analysis/competition/workbench.py --output artifacts/competition-analysis/final-01
python analysis/competition/workbench.py --output artifacts/competition-analysis/final-02
```

最终两个目录的文件名集合和所有 11 份文件逐字节一致，manifest 与文件哈希一致，
脚本哈希与当前脚本一致，三个 CSV 输入哈希重算一致。
结构计数/分母、技能分母、三份 SVG 的 XML 解析均通过。
原始 CSV 只读，数据记录与证据定位文件没有进入 Git；不写 D 盘。

指定入口 `.venv\Scripts\python.exe -m pytest -q tests/test_competition_analysis.py`
首先在加载既有 conftest/pandas 时失败，`_ctypes` DLL 报 ImportError，退出 1，未运行断言。
沿用仓库已记录的本机方法，在本批独占目录建立临时用户站点，使用基础解释器及已有依赖：

```powershell
$base = Join-Path (Get-Location) '.local/competition-env'
$site = Join-Path $base 'Python313/site-packages'
New-Item -ItemType Directory -Path $site -Force | Out-Null
Set-Content -LiteralPath (Join-Path $site 'competition.pth') -Value (Resolve-Path .venv/Lib/site-packages).Path -Encoding UTF8
$env:PYTHONUSERBASE = $base
$env:PYTHONPATH = (Resolve-Path src).Path
D:\Python\python.exe -m pytest -q -o cache_dir=.local/competition-pytest-cache
```

最后一次全仓结果 **157 passed in 23.29s**，退出 0（原 144 项 + 新 13 项）。
13 项覆盖词边界/否定、薪资负例、岗位排除、含换行 CSV、去重与分母、重复运行、
拒绝覆盖、缺字段失败清理、非空尾列计数、原始字符跨度、年份排除和课程占位接口。
非空尾列和原始空白跨度测试均先观察到断言失败，再修复并通过。
上述临时站点不改全局配置、已有 `.venv` 或项目依赖。

以下两条均未实际完成检查，退出 `-1073741502`（0xC0000142），无检查输出：

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
```

基础解释器经相同依赖入口启动 Ruff 也遇到相同 DLL 初始化失败。
未据此宣称 Ruff 通过。只把 Black 26.10.1 临时安装到 `.local/competition-format-tools/`，
整理本批两个 Python 文件；`--check --line-length 100 --target-version py311` 退出 0，
输出 `2 files would be left unchanged`。这不替代 Ruff 验收。
第一次 Black 安装因默认 pip cache 无写权限失败，改为本批 `.local/competition-pip-cache/` 后成功；
没有安装或改变分析运行依赖。

保持上面的基础解释器/临时站点环境，执行：

```powershell
python -m build --outdir .local/competition-build-final
python -m chanjiao_evidence run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --evidence data/evidence/internships.json --output .local/competition-cli/positive-01
python -m chanjiao_evidence run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --evidence data/evidence/internships.json --output .local/competition-cli/positive-02
```

- 隔离构建退出 0，生成 sdist 和 wheel；日志 `.local/competition-build-final.log`。
  单独检查 sdist 包含分析脚本、README、两个课程 JSON 和报告文档。
  分析脚本按设计属于源码材料，wheel 仍为原统计工具包，不新增 CLI 平台入口。
- 两次正常 CLI 均退出 0，输出 synthetic / internship，4 份报告逐字节一致。
- `git diff --check` 退出 0。最终交接文件无常见令牌/私钥模式命中，JSON 均可解析，
  10 处本地 Markdown 链接存在。没有将词面定位当作真实精确率或因果效果。
- SVG 仅做 XML 与布局数值检查，没有在图形程序中渲染验收；没有核验外部 URL。

### 实际发现与未完成项

2016 原始数据一条末尾空列非空，另有一条年份/日期不符；均单列计数排除，原文件未改。
2023 样本 Python 提及率 72.00%，平台10占 77.77%；需要按来源和人工标签复核，
不能把它写成真实技能需求或课程配比。各年的样本、缺失和薪资详见报告，不能作跨年总量趋势。

2024/2025 未提取、未运行回测；报告已给时间滚动、来源/月份可比切片、误差与失败记录框架。
2026 已参与探索，不是未触碰留出；真实学校课程、能力、就业和资源尚缺，只有示例接口。
未对真实文本抽取做人工标注精度评测，未在新机器或其他 Python 版本安装验收。

**交接结论：待独立验收，不可直接宣布可提交。** 协调者需：

1. 认领 C4 或指定验证者，独立复跑并复算；在正常环境完成 Ruff check/format，修复后重验受影响项。
2. 核对聚合结果的公开许可；保留 artifacts 忽略，尤其不要提交原始记录、数据库及证据定位文件。
3. 定稿 CHANGELOG，处理本批工作区文件的提交和 PR #3 更新/评审；实现者未执行任何 Git 写入或远端操作。

## revision 6 补充交接：格式修复与最小回顾性回测

本节是最新交接。C1–C3、C5/C6 均已由协调者独立验收通过。
不更改 W1–W4 任务或替协调者宣告通过，不执行 add/commit/push/gh。
`MANIFEST.in` 保留初次交接的一行追加，没有进一步修改；src、依赖和忽略规则未改。

### 修复与变更范围

- `workbench.py` 修复原 347/361/473 的 E501、283 附近条件表达式和 SVG f-string 空格。
  仅格式阶段与修改前 AST 完全一致；仅格式阶段全仓 **157 passed in 22.51s**。
  最终脚本新增显式 2024/2025 语义、可选 `--backtest` 与年度输入目录，原默认输入和统计规则不变。
- 新增 6 项测试（原全仓 157 项 → 163 项）：分年映射两例、预测截止与手算指标、
  空样本、零命中/无薪资、入口年份与确定性。前五项先观察到功能缺失失败，再实现通过；
  零提及用例另验证已实现的边界行为，不称为先失败的回归测试。
- `README.md` 补充提取/回测命令、指标公式和空值/并列规则。
  `docs/competition-analysis.md` 记录年度核验、实际误差、城市分组、失败与研究边界。
- `CHANGELOG.md` 只追加 W1–W4 记录链接、赛题解读和需求侧分析/回测条目，旧条目保留，交协调者定稿。

### 命令与可复核结果

沿用上文基础解释器与 `.local/competition-env` 用户站点，最终执行：

```powershell
$env:PYTHONUSERBASE = (Resolve-Path .local/competition-env).Path
$env:PYTHONPATH = (Resolve-Path src).Path
D:\Python\python.exe -m pytest -q -o cache_dir=.local/competition-pytest-cache-r4
D:\Python\python.exe analysis/competition/workbench.py --output artifacts/competition-analysis/verified-final-01
D:\Python\python.exe analysis/competition/workbench.py --output artifacts/competition-analysis/verified-final-02
D:\Python\python.exe analysis/competition/workbench.py --years 2016 2023 2024 2025 --annual-input-dir .local/analysis-data --backtest --output artifacts/competition-analysis/verified-backtest-01
D:\Python\python.exe analysis/competition/workbench.py --years 2016 2023 2024 2025 --annual-input-dir .local/analysis-data --backtest --output artifacts/competition-analysis/verified-backtest-02
```

- 最终全仓 **163 passed in 23.19s**，退出 0；日志 `.local/competition-revision-4/pytest-final.log`。
- 正式画像 verified-final-01/verified-final-02 各 11 文件，名称集合和全部文件字节相同，脚本哈希对应最终脚本。
  与旧的 final-01 相比，10 个内容文件逐字节不变，manifest 仅 `script_sha256` 改变；
  原岗位族、技能、薪资、证据跨度、规则和课程占位的数字/内容未变。
  旧的 final-03/final-04 目录受本机 Windows 权限限制为空，正式复核改用 verified-final-01/02。
- 回测 verified-backtest-01/verified-backtest-02 各 13 文件，名称集合与全部文件字节相同；
  终端入选数依次为 12678、4035、3272、3560，新增年度实际结果见分析报告，不在此重复列分数。
- 通过本机已有 `extract_rar_member` API 仅提取两个明确 CSV，退出成功并核对大小/CRC32；
  CSV 均在 `.local/analysis-data/`。原包提取前后大小、mtime 未变，没有写 D 盘。
  两个年度的提取元数据和全文件质量核验在 `.local/competition-revision-4/extract-*.json`、
  `audit-*.json`，保留月份、缺失、来源与按平台类别常见值。
- `.local/competition-revision-4/verify_final.py` 不导入工作台，从输出 CSV 另行复算
  两折 × 三地区 × 两方法的 72 项指标，均吻合；另核对两遍字节、manifest、
  四份输入 SHA-256、SVG XML 和 16 处本地 Markdown 链接。
  结果 `.local/competition-revision-4/verification-final.json`。这是实现者的另一路复算，不能代替协调者独立验收。
- 构建及正常 CLI 均退出 0，命令如下。CLI 输出 synthetic / internship；sdist 包含分析脚本、占位 JSON、README、TASKS。
  构建日志 `.local/competition-revision-4/build-final.log`，不把构建当作新机器安装验证。

```powershell
D:\Python\python.exe -m build --outdir .local/competition-revision-4/dist-final
D:\Python\python.exe -m chanjiao_evidence run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --evidence data/evidence/internships.json --output .local/competition-revision-4/cli-01
```

### Lint/format 环境限制与验收结论

`.venv\Scripts\python.exe -m ruff check .` 和 `-m ruff format --check .` 均无检查输出，
退出码 3221225794（有符号 -1073741502 / 0xC0000142，DLL 初始化失败）；
基础 Python 经上述用户站点启动 Ruff 仍同样失败。**不宣称 Ruff 已通过。**
本批两个 Python 文件均无超过 100 字符的行，临时 Black 辅助命令退出 0：

```powershell
$env:PYTHONPATH = (Resolve-Path .local/competition-format-tools).Path
$env:BLACK_CACHE_DIR = (Resolve-Path .local/competition-black-cache).Path
D:\Python\python.exe -m black --check --line-length 100 --target-version py311 analysis/competition/workbench.py tests/test_competition_analysis.py
```

输出 `2 files would be left unchanged`；不替代协调者正常 `.venv` 中的 Ruff check/format。
`git diff --check` 退出 0；交接文件未发现常见令牌/私钥/邮箱模式；本批数据、数据库和证据定位文件均留在已忽略目录。

尚未完成：来源/月度及行业/学历/经验匹配、平台身份确认、行业/平台误差分组、跨年企业转发隔离、
企业簇区间、真实技能人工标签、独立留出、新机器/其他 Python 安装和图形渲染验收。
2026 已参与探索，回测不形成因果或培养效果结论；完整限制统一见分析报告。
最终独立验收、Ruff 复验、CHANGELOG 定稿及提交/PR 均交协调者。

## revision 8 交接：第 4 批共同支持回测

这是第 4 批最新交接，C7–C9 均已由协调者独立验收通过。
修改六个受版本控制的文件：`workbench.py`、对应测试、本目录 README/TASKS、
`docs/competition-analysis.md`、`CHANGELOG.md`。没有改 src、原始 CSV、数据库、依赖或忽略规则。
开始时分支 `feat/local-data-warehouse`、HEAD `2b76d5e`、工作区干净；本轮没有 Git 写入或 gh 调用。

### 为什么这样改

原年度聚合无法检查联合支持。现在可选保留年内去重后的紧凑特征，逐层取所有训练年与目标年交集，
再取完整组合交集；断层即停止，不借全年分数补齐。两种方法复用同一计算，全年对照保持原口径。
五维分组枚举原值并集，空组、小样本、零命中和无优势均保留；跨年企业/岗位只输出疑似重叠计数。
完整算法、机器字段与分母见 [README](README.md#共同支持切片与误差组)，
实际样本流、指标、失败组和泄漏边界统一见 [分析报告](../../docs/competition-analysis.md#第-4-批共同支持的可比切片)。

### 命令、环境与输出

基础解释器配本机已有临时用户站点；没有修改全局配置或 `.venv`：

```powershell
$env:PYTHONUSERBASE = (Resolve-Path .local/competition-env).Path
$env:PYTHONPATH = (Resolve-Path src).Path
D:\Python\python.exe -m pytest -q -o cache_dir=.local/competition-batch4/full-pytest-cache
D:\Python\python.exe analysis/competition/workbench.py --years 2016 2023 2024 2025 --annual-input-dir .local/analysis-data --matched-backtest --output artifacts/competition-analysis/verified-matched-final-01
D:\Python\python.exe analysis/competition/workbench.py --years 2016 2023 2024 2025 --annual-input-dir .local/analysis-data --matched-backtest --output artifacts/competition-analysis/verified-matched-final-02
D:\Python\python.exe .local/competition-batch4/verify.py
D:\Python\python.exe -m build --outdir .local/competition-batch4/dist
D:\Python\python.exe -m chanjiao_evidence run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --evidence data/evidence/internships.json --output .local/competition-batch4/cli-01
```

- 新增 10 个测试实例，首先观察到函数/开关缺失失败；实现后相关文件 **29 passed**。
  覆盖六种断层、联合组合无支持、缺失平台/空组、手算误差/零命中/稳定性、入口/确定性/输入不变。
  一个空组用例先误设零分母覆盖率为 0，按既定口径修正为 null；不把此修改说成实现修复。
- 全仓自测先为 **173 passed in 26.02s**，Black 整理后最终 **173 passed in 24.75s**，退出 0。
  日志 `.local/competition-batch4/pytest.log`、`pytest-final.log`。
- 两次实际分析均退出 0，原入选数为 12,678 / 4,035 / 3,272 / 3,560。
  共同支持后 2024 为 543 / 89 / 597，2025 为 358 / 42 / 486 / 39；
  目标覆盖 18.25% / 1.10%。低覆盖、平台13单条、电子行业两条和大量空组均未删去。
- `verified-matched-final-01/02` 各 **14 文件逐字节一致**，包括 3.35 MB 的分组 JSON 与 manifest。
  manifest 输出集合、当前脚本哈希、课程占位哈希、四份原 CSV 的实际字节数与 SHA-256 重算一致。
  第一遍扫描期间仅执行 Black 格式整理，Black 默认安全模式检查语义；最终两遍产物字节一致且脚本哈希一致。
  没有覆盖或修改 verified-final-01/02、verified-backtest-01/02。
- `.local/competition-batch4/verify.py` 不导入当前工作台，依据输出另算 **880 个方法块**的
  MAE/TVD/Top-5/薪资误差与改善标记，核对分层覆盖率、分组样本守恒。
  另用只读 `git show HEAD:analysis/competition/workbench.py` 加当前聚合 CSV 重建全年画像，
  三地区两折全年结果与旧 HEAD 实现完全一致；不是重复调用当前实现来证明自己。
  结果 `.local/competition-batch4/verification.json`；仍属于实现者自检，不代替协调者验收。
- 隔离构建退出 0，生成 sdist/wheel，日志 `.local/competition-batch4/build.log`；
  检查 sdist 包含分析脚本和测试。正常 CLI 退出 0，输出 synthetic / internship。
  这些不是新机器安装或跨 Python 版本验证。

以下命令在 `.venv` 和基础解释器两种入口均退出 **-1073741502（0xC0000142）**，无检查输出：

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
D:\Python\python.exe -m ruff check .
D:\Python\python.exe -m ruff format --check .
```

**Ruff check/format 未完成，不宣称通过。** 只使用已存在的 Black 辅助工具：

```powershell
$env:PYTHONPATH = (Resolve-Path .local/competition-format-tools).Path
$env:BLACK_CACHE_DIR = (Resolve-Path .local/competition-black-cache).Path
D:\Python\python.exe -m black --check --line-length 100 --target-version py311 analysis/competition/workbench.py tests/test_competition_analysis.py
```

退出 0，`2 files would be left unchanged`，两个文件无超过 100 字符行；不替代 Ruff。
`git diff --check` 退出 0，21 个本地 Markdown 链接存在；外部链接未访问。
六个交接文件未命中常见令牌、私钥、邮箱模式；原始数据与证据定位文件均留在忽略目录。

### 尚未完成与交接结论

平台真实身份及采集口径未确认；没有隔离企业/跨年转发、簇区间、人工技能标签或独立留出，
没有做新机器/其他 Python 版本安装和 SVG 图形渲染验收。
2026 已参与探索，目标年协变量参与了支持选择，只作回顾性描述，不写因果与四年收益结论。
协调者已完成正常环境 Ruff check/format、独立验收、CHANGELOG 定稿与提交。
本轮结论：**实现、实际运行与协调者验收已通过。**
