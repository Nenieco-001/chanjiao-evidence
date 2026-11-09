# 正式开发任务板

## 本地数据仓库 · revision 8

协调者为 root，分支为 `feat/local-data-warehouse`。本轮先完成本地开发、真实数据试运行和验收，再沿用用户此前允许推送特性分支、创建 PR 和请求评审的授权交付通用代码。原始数据及实际指标留在本机，合并由用户执行。

2026-11-10 由本轮 Codex 接手 W4，独立复跑上一轮 W1–W3 的冻结实现。任务板以本文件为准，验收产物独占 `.local/codex-verify/`。Codex OAR 在自身沙箱内遇到 `.venv`/Ruff DLL 初始化失败与 `.git/index.lock`/gh 写入限制；协调者在正常 `.venv` 中复验通过（144 项测试、ruff、format），因此 W1–W4 标为完成、验收通过。Codex 的环境阻断记录保留在下文，便于追溯；未修改 W1–W3 源码或测试，也未改动原已暂存的赛题文档。

### W1 · 压缩包版本核验

- 负责人为 archive_auditor，状态为完成，验收通过，revision 8。本轮完整测试覆盖归档测试；真实 ZIP 两次比较均内容相同，CRC 通过，比较报告字节一致。
- 写范围为 `src/chanjiao_evidence/archives.py`、`tests/test_archives.py`，真实核验记录仅写 `.local/warehouse-archive-audit/`。
- 无前置依赖。核验两份规划 ZIP 的完整性和规范化成员 SHA-256，输出相同、仅一方有、内容冲突的清单。完整性与内容正确性分开记录。
- 提供 ZIP 比较、RAR 成员目录、单成员落盘函数，原包只读。解压写指定新路径，CRC 失败或中断清理本次临时文件。禁止整库解压、输出数据行或执行压缩包内容。
- 验收为重复副本、坏 ZIP、路径差异、不同内容、拒绝覆盖和失败清理均有测试，真实 ZIP 比对完成。

### W2 · DuckDB 招聘仓库

- 负责人为 warehouse_builder，状态为完成，验收通过，revision 8。本轮完整测试覆盖仓库测试；真实单年度重新入库、幂等重跑、数量受限的汇总、Parquet 行数与哈希核对通过。
- 写范围为 `src/chanjiao_evidence/warehouse.py`、`tests/test_warehouse.py`，临时文件仅写 `.local/warehouse-builder/`。
- 根据下面接口独立实现 CSV 入库、版本登记、质量汇总及 Parquet 导出。使用 DuckDB 2.0.0，限制内存与线程，CSV 按字符串保留原值，SQL 产生类型化视图，质量异常留计数。
- 验收包括 BOM/引号换行、19/20/23/24 列、来源平台缺失计数、版本隔离、同版本重跑幂等、不同内容版本冲突、CSV 损坏回滚、异常薪资日期、精确重复、Parquet 往返和汇总数量上限。不能把原始记录或职位描述返回给 LLM。
- revision 6 追加整数小数年份归一化计数，分数年份继续保留为异常；已有数据库通过同内容幂等调用刷新类型化视图，原记录不重复插入。

### W3 · 命令行与真实试运行

- 负责人为 root，状态为完成，验收通过，revision 8。本轮六个仓库 CLI 子命令均退出 0；原有正效应、零效应 CLI 及报告确定性通过。具体指标留在本机。
- 写范围为 `cli.py`、`tests/test_warehouse_cli.py`、共享配置和文档、任务板。
- 依赖 W1/W2。集成 `warehouse compare-zip`、`warehouse list-rar`、`warehouse unpack`、`warehouse ingest`、`warehouse summary`、`warehouse export`。
- 选择一个实际招聘年度成员，完整校验并导入，默认输出摘要与计数，代码上下文中只出现元数据和汇总。原数据留在 D 盘。
- 验收为可重复执行的入库、摘要与导出命令，明确范围和质量计数，保持原有因果分析入口兼容。

### W4 · 独立验收

- 负责人为 root（接手上一轮实现的独立验收），状态为完成，验收通过，revision 8。Codex OAR 沙箱内的 `.venv`/Ruff DLL 失败与 Git 写入限制保留为环境记录；协调者在正常 `.venv` 中复验 144 项测试、ruff、format 全部通过，W1–W4 可提交。
- 源码与测试只读；验收独占 `.local/codex-verify/`，协调者仅更新本任务板和文档中的验收链接。
- 全量测试、ruff、format、build、原有 CLI、仓库 CLI、版本与哈希、文档链接和公开 diff 检查。逐项给出 PASS/FAIL 与可提交结论，未完成的全量核验单列。

### W4 · 2026-11-10 独立验收记录

- **FAIL，指定测试入口**：`.venv\Scripts\python.exe -m pytest -q` 在加载 conftest 时退出 4，`_ctypes` 报 `ImportError: DLL load failed while importing _ctypes: 出现了内部错误。`。串行和隔离模式重现 DLL 初始化失败，没有进入测试断言。
- **PASS，完整测试替代入口**：使用同一 Python 3.13.7 的基础解释器 `D:\Python\python.exe`，通过本轮临时用户站点加载现有 `.venv/Lib/site-packages`，运行 `-m pytest -q -o cache_dir=.local/codex-verify/pytest-cache`，结果 `144 passed in 21.80s`，退出 0。首次只设 PYTHONPATH 时有 142 通过、2 个 CLI 子进程因依赖路径丢失而失败；临时用户站点让子进程使用同一套依赖，完整重跑后通过。未改测试、未跳过测试、未重装依赖。
- **FAIL，静态检查**：`.venv\Scripts\python.exe -m ruff check .`，退出 `-1073741502`（`0xC0000142`，DLL 初始化失败），无检查输出。直接启动 Ruff、串行重试和补充基础 Python 的 DLL 搜索路径仍失败。安装包 RECORD 中的 Ruff 可执行文件哈希与实际文件一致，未发现文件损坏，启动失败的底层原因尚未定位。
- **FAIL，格式检查**：`.venv\Scripts\python.exe -m ruff format --check .`，同样退出 `-1073741502`，无检查输出。不能把“没有输出”当作检查通过。
- **PASS，离线非隔离构建**：按下列命令退出 0，生成 `chanjiao_evidence-0.3.0.tar.gz` 和 `chanjiao_evidence-0.3.0-py3-none-any.whl`。核对 wheel 包含两个新增模块及 `duckdb==2.0.0` 依赖；没有执行联网隔离构建或新环境安装。

  ```powershell
  $sp = 'C:\Users\RE5a\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\Lib\site-packages'
  $env:PYTHONPATH = $sp
  .venv\Scripts\python.exe -m build --no-isolation --outdir .local/codex-verify/dist
  ```

- **PASS，仓库 CLI**：用上述基础解释器及同一套依赖运行 `-m chanjiao_evidence warehouse`。实际执行 `compare-zip` 两次、`list-rar`、`unpack` 一个明确的 2026 年 CSV、`ingest` 两次、`summary --limit 10` 两次和 `export`，共 9 次调用均退出 0。提取 CRC、源 CSV SHA-256、幂等状态 imported/skipped、行数、Top-N 上限及 Parquet SHA-256/往返行数均核对通过；两次 ZIP 比较及两次 summary 报告分别字节一致。RAR 原包大小与修改时间前后一致，程序没有写入 D 盘。
- **PASS，原有 CLI**：正效应带文献输入运行两次、零效应运行一次，3 次调用均退出 0；分别选择 internship、unchanged。相同输入的四个产物字节一致，manifest 中的报告哈希与文件一致。合成结果仅检验实现。
- **PASS，文档与公开改动**：14 处本地文档链接存在，`git diff --check` 和 `git diff --cached --check` 退出 0；16 个待交付文件均为代码、测试、配置或文档。未发现原始数据产物、个人级记录或凭据，常见凭据模式扫描无命中；已暂存的 `docs/competition-brief.md` 与工作区逐字节相同。新增 DuckDB 两个文档入口已打开，固定版本许可证链接未能完成外部抓取，不据此判定链接失效。

验收日志与各步骤报告保存在本机 `.local/codex-verify/`，不进入 Git。完整测试的临时入口如下，仅影响当前进程和本轮目录：

```powershell
$verifyRoot = (Resolve-Path .local/codex-verify).Path
$userSite = Join-Path $verifyRoot 'userbase/Python313/site-packages'
New-Item -ItemType Directory -Path $userSite -Force | Out-Null
Set-Content -LiteralPath (Join-Path $userSite 'warehouse-verification.pth') -Value (Resolve-Path .venv/Lib/site-packages).Path -Encoding UTF8
$env:PYTHONUSERBASE = Join-Path $verifyRoot 'userbase'
$env:PYTHONPATH = (Resolve-Path src).Path
D:\Python\python.exe -m pytest -q -o cache_dir=.local/codex-verify/pytest-cache
```

**结论：Codex OAR 环境内不可标为通过；协调者在正常 `.venv` 复验后 W1–W4 通过。** 功能证据已齐；未完成项为联网隔离构建、新环境安装、其他 Python/操作系统组合、全量年度与跨版本质量核验，以及真实培养效果识别。单年度试运行不替代这些验证，不形成因果结论。

**交付：** 用户此前已授权提交、推送和 PR。Codex OAR 的 `git index.lock`、gh 令牌失效与连接器审批限制记录保留；协调者以本机权限完成本轮提交、推送和 PR，合并仍由用户执行。

### W4 · 协调者复验（2026-11-10）

- `.venv\Scripts\python.exe -m pytest -q`：**144 passed in 22.55s**，退出 0。
- `.venv\Scripts\python.exe -m ruff check .`：**All checks passed**，退出 0。
- `.venv\Scripts\python.exe -m ruff format --check .`：**43 files already formatted**，退出 0。
- 离线非隔离构建、原有 CLI、仓库 CLI、哈希与文档链接沿用同轮 Codex 证据；Codex OAR 的替代入口也报告 144 passed。
- 结论：W1–W4 验收通过；Codex OAR 的 DLL/Git 阻断是执行环境差异，不是代码失败，记录保留以便追溯。

### 接口约定

W1 提供 `compare_zip_archives(left: Path, right: Path) -> dict`、`list_rar_members(archive: Path, unrar: Path) -> list[dict]`（每项至少 name、size、crc，属于声明信息）、`extract_rar_member(archive: Path, member: str, destination: Path, unrar: Path) -> dict`（返回输出 size、sha256、CRC 是否通过）。调用原机 UnRAR，测试不能要求 CI 安装 WinRAR。

W2 提供 `ingest_recruitment(csv_path: Path, database: Path, dataset_id: str, version: str, *, expected_year: int | None = None, memory_limit: str = '512MB', threads: int = 2) -> dict`、`summarize_recruitment(database: Path, dataset_id: str, version: str, *, limit: int = 10) -> dict`、`export_recruitment(database: Path, dataset_id: str, version: str, destination: Path) -> dict`。

摘要按指定 dataset_id/version 计算总行数、精确重复、缺失与无效字段计数、日期范围、按年/城市/学历汇总，列表上限 1–50。保留异常原值、记录来源路径与 CSV SHA-256；同版本同内容重复调用不增加行数，不同内容同版本报错。事务失败不能留下成功登记或半份记录。Parquet 导出选择明确版本、使用新路径，失败清理。

原有 `run` 和面板格式独立保留，招聘数据不会自动变成学生就业结果。

## R1 · DSH 交付复核

- 负责人为 root，状态为完成，revision 3。重新执行 85 项测试、静态检查、隔离构建与四次 CLI，结果和哈希均通过。
- 范围为只读提交 4210ef9、1d63244 及其验收记录，独占 `.local/dsh-followup-review/` 输出复核产物。
- 前置为 PR #2 已提交；验收为测试、静态检查、构建、CLI、报告确定性及文献隔离，发现实际错误后再登记修复范围。复核记录与任务板由协调者更新。

## R2 · Codex 评审触发修复

- 负责人为 root，状态为完成，revision 3。已定位本仓库缺少 GitHub 集成授权，按用户批准加入指定仓库列表。重新请求后，Codex 添加了 👀 并发布 Running 状态，触发链路已恢复。
- 范围为 GitHub 集成、仓库评审设置、PR #2 评审评论和响应，不改代码。
- 用户已授权检查和修复；涉及新增安全访问的授权由用户完成。验收为定位配置问题、完成允许的修复并观察重新请求的实际回应。合并仍由用户执行。
- 触发核验见 [PR #2 的评审请求](https://github.com/Nenieco-001/chanjiao-evidence/pull/2#issuecomment-6741175577) 和 [Codex 状态](https://github.com/Nenieco-001/chanjiao-evidence/pull/2#issuecomment-6741184787)。评审是否完成及其发现以 PR 最新记录为准。

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
