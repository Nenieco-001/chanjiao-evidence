# 第 2 批需求侧工作台任务板

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
