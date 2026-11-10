# 当前任务

本文件是唯一活动任务板。协调者为 root，当前 revision 28。F1–F5 为 revision 15 的已验收基线。目标、研究口径、路线和偏移分别由 project.md、roadmap.md、status.md 维护。历史交接已做本机备份，原始数据与计算产物留在本机。

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
- 验收为至少一个实际培养方案的课程切片可被 F3 接入，所有数值有官方原文位置，原文件仅在本机；学校批准状态另行登记。

## F3 · 课程候选与约束

- 负责人为 curriculum_builder，状态为验收通过，revision 15。本轮独立运行 38 项课程测试通过，包含零增量仅归入基线的回归。全量回归的阻断单列于 F5。
- 写范围为 `src/chanjiao_evidence/curriculum.py`、`tests/test_curriculum.py`。
- 先按下方接口开发，F2 可并行。读取真实课程输入与独立情景配置，生成保持原方案及有限候选，检查课时/学分守恒、课程底线、先修与资源约束，保留不可行和无优势结果。
- 输出课程动作及理由、输入依据、约束检查、评价和修订记录。内容覆盖与学生结果分开；就业效果缺实证时返回明确缺项，不从招聘词频推算收益。
- 验收为真实课程格式、未知/缺失学时、非法动作、不可行约束、保持原方案、确定性及来源隔离有测试。平台范围保持，自动代入文献收益和改动既有需求分析都排除在外。

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

## G1 · 专业要求与事实

- 负责人为 program_facts，revision 16，状态为独立验收通过。50门课程与十模块规则已核对，107项独立探针通过。写范围仅 `data/curricula/cufe-2025-program.json`，原文及提取证据写独占忽略目录。
- 依赖 F2。从同一官方 PDF 提取 147 学分、十类模块底线、课程模块/必选修/讲课实验实践及原文位置，缺项保留。不可把全部选修池相加当作学生实际选课。
- 验收为规则合计147、已有十门课程逐项对应、实践环节与专业综合实践类别分开，字段与原文独立核对。

## G2 · 完整约束与可执行机制

- 负责人为 program_policy，revision 16，状态为独立验收通过。80项定向测试与54项独立探针通过，招生人数浮点边界和调整后数值溢出已修复。写范围为 `src/chanjiao_evidence/strategy.py`、`tests/test_strategy.py`、`src/chanjiao_evidence/curriculum.py`、`tests/test_curriculum.py`。全局文档和 CLI 由 root 修改。
- 依赖 G1 的公开规则接口，读取课程候选、选课路径与政策配置。检查模块底线、未选 donor、富余学分路径，保留失败并重新评价修订候选。方向容量、分流时点与条件、招生反馈阈值/调幅/周期/时滞及风险必须显式给出。
- 验收为跨模块缺1学分反例、路径边界、未知反馈保持原规模、合成压力测试与真实状态隔离。先增加大整数及有限数聚合溢出回归，再作最小入口修复。

## G3 · 历史证据与三情景

- 负责人为 effect_scenarios，revision 16，状态为独立验收通过。独立105项本模块及相关测试通过，指标误标、零优势容差和比例差点值范围已修复。写范围为 `src/chanjiao_evidence/scenarios.py`、`tests/test_scenarios.py`、`data/examples/effect-scenarios.json`。
- 依赖已有两项实习证据卡。保留指标、单位、标准误与源位置，以显式迁移系数和同单位偏差计算悲观/基准/乐观区间，包含零与负结果。处理定义不匹配时阻止外推，只输出文献条件性参照。
- 验收为对数单位与比例差值分开、系数来源和偏差均可追溯、文献效应与本校效果分列，返回缺项与优势消失阈值。新行为先写失败测试。

## G4 · 集成、材料与打包

- 负责人为 root，revision 16，状态为审阅版验收通过。源码19项定向测试与50项独立探针、实际材料234项核对通过。写范围为 CLI、对应测试、全局文档、方案配置、材料构建与提交包模块。依赖 G1–G3。
- 正常入口生成统一 JSON/Markdown 与证据缺项，复用原子发布和拒绝覆盖。将官方四任务、四类材料与许可逐项写入可机读提交清单，缺项生成审阅版及原因，完成证据后才放行正式包。
- 验收为全量测试、Ruff、构建、新旧入口两次确定性、包内哈希与安全路径检查。报告/PPT需渲染检查，视频需真实成片且不超过300秒，支撑材料含可复核输入与脚本。

## G5 · 独立复核与远端

- 负责人为 root 协调独立验证，revision 26，状态为既有提交基线远端复核完成、G8增量待Lead验收。验证者只读，证据留在独占忽略目录。远端发现的路径P1由revision 17修复并重新评审。
- 已提交基线 `021e5ff` 并推送，PR #4 已创建，远端 CI 成功，Codex 对该提交评审完成且未发现重大问题。合并留给人类贡献者。
- 后续每项实现先设待验收，由独立验证者检查契约、反例、数据和材料范围；修复交回原 owner，复验后由 root 统一提交与推送。
- 2026-11-11只读核对PR #4，远端head与本地HEAD均为 `ffa685b76eed08b641836a26778efe97bb53b990`。Codex摘要明确该提交completed、无新问题，PR工作流42891333132的Ubuntu/Windows × Python3.11/3.13四任务全部成功，逐项pytest、原生Ruff、format、build和正常CLI步骤成功。旧P1线程为outdated但尚未手工resolved，由Lead处理讨论状态。该结论覆盖已提交基线，本工作区G8增量另行验收。原始API记录保存在 `.local/g8-followup-20261111-01/remote-review-raw.json` 和 `remote-jobs.json`。

### revision 16 实际验收

- 全量 `python -m pytest -q -p no:cacheprovider` 为351 passed in 16.45s，Ruff check通过，format检查为51 files already formatted，标准隔离build生成sdist与wheel成功。
- 新strategy入口两次三产物逐字节一致，五份输入、十五个模块源码与结果哈希吻合。旧curriculum、run及warehouse回归131项通过，42个本地链接与锚点有效。
- 实际审阅材料包含7页PDF、12页PPTX、232秒H.264视频、数据与代码。234项独立检查通过，79个白名单文件和manifest的CRC、字节与SHA-256吻合，两包逐字节一致。包内源码复现三产物一致，已有依赖环境下通过。
- 包状态为review_only，十项缺口保留。正式打包模式实际退出2且没有发布。视频为无旁白的结果演示，完整解码2320帧通过。原生符号链接实机测试因Windows权限跳过，受控拒绝分支通过。
- 证据分别保存在 `.local/submission-phase-r16/`、`.local/submission-gap-review/g1/`、`.local/submission-gap-review/g2/`、`.local/scenario-review/` 与 `.local/submission-review/`。最终材料与压缩包留在Git忽略的artifacts目录。

## G6 · 公开基线与条件分析

- 负责人为 root，revision 26，状态为本机实现与既有提交基线远端代码复核完成。远端验收记录见G5，研究证据缺口继续按G9登记。用户确认暂时无法取得校级规模和就业汇总，继续公开资料与条件分析。写范围为公开来源证据卡、对应分析模块/测试及核心文档；D盘原文只读。
- 先核对全国就业报告的报告年份、毕业届别、半年后指标与专业类层级，交叉检查出版信息。整理可公开引用的少量事实和来源，原书与记录留在本机。
- 再用课程内容覆盖、方向结构及规范化规模情景分别量化三维指标，保留代理含义、未知观测与参数来源。文献收益与目标措施不对应时继续返回未识别，优先补同定义教学改革证据。
- 验收为三维输入/输出、分母、公共基线与假设分离，零/负/无优势和参数敏感性保留，无法完成的正式要求继续阻止正式提交包放行。

### revision 17 当前实现

已接入北京152条岗位、12词面256次提及的既有聚合。显式课程名称支持的权重为111，覆盖下界43.36%。拟定内容下界70.70%，条件增量0至27.34个百分点。三种方向基线假设保留劣势、无优势与改善，规模情景差额为-64.8、-24.4与16.0，真实学校观测仍为 null。公开就业汇总另行登记，未自动代入学校反馈。

远端对2e849ed评审发现父目录链接绕过白名单禁入的P1。已增加逐层lstat检查，拒绝符号链接及Windows重解析点。控制回归先失败后通过，本机真实junction反例确认拒绝。原生符号链接因权限限制跳过，Linux实机分支由远端CI核验。

本机最新全量为378 passed、1 skipped，Ruff两项通过，53个文件格式正确。曾出现一次旧需求入口Windows发布WinError 5，已补限次重试及永久失败清理回归，32项需求工作台测试通过，隔离模式下正常CLI两次成功。规范化规模运算溢出回归先失败后通过。代码修复后重新生成带七输入与十六模块源码哈希的方案结果。

正式材料清单的S.evolution按完整自动挖掘范围保留partial。已验证有限候选的失败修订与重算，尚未验证从需求和课程关系自动提出更广方案。revision17审阅包因此保留十一项未齐，四类材料文件通过。

校内新试点、真实未来观测及学校实施批准分别记录，竞赛验证可采用有来源的条件情景。当前仍保留任务证据与公开范围缺项，最终放行依据官方要求和实际验收。

## G7 · 目标措施的效果依据

- 负责人为 root，revision 19，状态为验收通过。写范围为新增课程项目证据卡、相应情景配置、scenarios.py及相关测试，证据目录为 `.local/g7-evidence-20261111/`。优先查阅与现有课程内项目实践、软件工程内容承接相符的公开教学改革，记录原有教学方式、处理动作、对照与成绩/任务表现。
- 2026-11-11 复验：输入中文编码恢复（两文件 0 问号，高字节 3155/600），保留结构、来源链接、SHA-256 与数字；`scenarios.py` 增加 `standardized_mean_difference`；专项 15 passed，全量 393 passed/1 skipped，Ruff/format 通过，0.4.0 构建成功。
- 证据边界：4 张卡片分别承担设计经验、无一致优势的流程对照、大学亚组 SMD 参照和宽背景主动学习对照；reference SMD 0.116、CI [0.027, 0.204]，三情景 -0.03 / 0 / 0.058；目标措施仍为 unidentified，未把文献参照当本校效果。
- 对照当前本来已有实验/实践课的事实审查文献适用性，避免把实习参与效应或讲授与主动学习的总体比较直接当作增加16学时的收益。
- 验收需要可复核的措施与结果、零或负结果、单位和时间窗、识别条件与迁移范围。按证据强度收缩参数，补课程增删合并内容、资源与风险量化，再统一更新正式材料。

## G8 · 正式材料与提交一致性

- 负责人为 root，revision 27，状态为验收通过。写范围为 `src/chanjiao_evidence/submission.py`、纯字节清单校验辅助模块、相应测试、G9源清单配置及本任务板G段。数据契约与 CHANGELOG 仅同步功能事实，文风与H3材料由Lead负责。
- Lead 预跑：`data/examples/submission-checklist.json` 已同步为交付包状态，T3 evidence 加入 G7 两个 JSON；候选材料 `artifacts/submission-review-g8-candidate/` 的 review 包为 `review_only`、缺 11 项；`--require-ready` 退出 2；`tests/test_submission.py` 19 passed/1 skipped。
- 依赖 G7。正式提交清单仍需 Codex 复核：15 个 requirement ID、S.evolution/T3 保持 partial、G7 证据入包、正式模式拒绝未齐包；review_only 与正式提交分列，正式包保持拒绝。
- 本轮发现旧候选 manifest 登记的 scenarios.py 哈希失配。新增可选 provenance 绑定，复用打包实际字节核对输入、产物与完整源码角色，失配进入审阅缺项并阻止正式发布。旧清单兼容，失配反例先失败后通过。候选 `artifacts/submission-review-g8-verified/` 为 98 项白名单，两组共 52 项绑定全部匹配。主 JSON/Markdown 与原候选逐字节一致，G7 SMD 独立附件注明指标边界，两组均使用正常 strategy 入口两次复现，包内代码再跑的三产物分别一致。
- 实际命令使用 `.local/g8-audit-20261111/run_py312.py` 和受支持的捆绑 Python 3.12，补充依赖仅在本轮忽略目录。`pytest tests/test_submission.py tests/test_provenance.py -q` 为 37 passed、1 skipped；最新全量 `pytest -q -p no:cacheprovider --basetemp .local/g8-audit-20261111/final-tests` 为 411 passed、1 skipped（35.48s）。原 `.venv` 全量 pytest 退出4，原因是 `_ctypes` DLL 导入失败。原生 `ruff check . --no-cache` 与 `ruff format --check . --no-cache` 均退出 -1073741502。同版官方 Ruff WASM 0.17.4 对四个变更 Python 文件检查零诊断、格式一致，随后对39个公开Python文件只读复查同样通过，该结果单列为补充检查。
- 两次正常 bundle 退出0，ZIP逐字节一致，CRC、98项文件哈希及15个唯一要求ID通过，11项partial与G9表一致。`--require-ready` 退出2且无产物。标准隔离 build 退出1，pip获取Windows目录时注册表查询失败；捆绑Python的 `-m build --no-isolation` 退出0，生成0.4.0 wheel/sdist，wheel全模块与源码字节一致，sdist含新增模块。G7两文件仍为0问号，高字节3155/600。31个本地链接与锚点有效，git diff --check通过。H段和受保护源码未改，公开差异未带入原始记录、凭据或受限文件。
- 日志、完整CLI参数、哈希、构建包、同版WASM检查及自检脚本均在 `.local/g8-audit-20261111/`。本轮为实现者自检，Lead独立复验与原生Ruff仍待完成，构建续验见下两条。图文材料继续展示原主指标，G7正式图文整合由Lead负责。G9复核结果见下节，下一步由Lead验收本地增量。
- 续验记录在 `.local/g8-followup-20261111-01/`。从交付ZIP（SHA-256 `60658e9bec0a463741db085f4250bd43aff6926309551dc3d38562ef5b33784f`）按逐文件哈希提取源码，使用捆绑Python3.12执行 `-m pip install --target <全新依赖目录> <随包代码>[dev]`，默认PEP517隔离构建及安装退出0。项目、NumPy、pandas、SciPy、statsmodels、DuckDB、pytest的导入位置均位于新目录。依赖为pandas3.1.1、NumPy2.5.4，statsmodels0.15.0、DuckDB2.0.0保持仓库指定版本，原项目.venv未注入。
- 随包代码执行 `-m pytest tests/test_submission.py tests/test_provenance.py -q -p no:cacheprovider --basetemp <独占目录>` 为37 passed、1 skipped（23.60s），全量同参数为411 passed、1 skipped（32.13s）。安装后的正常strategy入口按两套指标各跑两次，三产物分别与冻结值一致；合成旧run入口两次四产物一致；bundle两次退出0且字节与原ZIP完全一致，正式模式退出2且无文件。39个公开Python文件同版WASM补充检查再次通过。原生Ruff新装副本连 `--version` 也以0xC0000142启动失败，`-m ruff`包装进程返回4294967295。默认 `-m build` 仍在临时虚拟环境的pip目录查询处失败，pip默认PEP517隔离构建成功的结果单列。
- 用同一全新依赖目录回到当前工作区执行 `-m pytest -q -p no:cacheprovider --basetemp .local/g8-followup-20261111-01/pytest-workspace`，退出0，411 passed、1 skipped（29.18s），输出为 `pytest-workspace.log`。最终 `handoff_audit.py` 核对31个本地链接/锚点、11项partial集合、ZIP所有文件哈希和源码字节，git diff --check通过。本轮公开事实更新仅tasks/status两文件，其余开工时未提交文件的字节哈希一致。
- 交接点续核记录在 `.local/g8-gate-20261111-02/`。当前快照全量 `-m pytest -q -p no:cacheprovider --basetemp <本目录>/pytest` 退出0，411 passed、1 skipped（33.76s）；`-m ruff check . --no-cache` 和 `-m ruff format --check . --no-cache` 均退出4294967295，同版WASM对39个公开Python文件检查及格式复核通过。清单、31个链接/锚点、原ZIP哈希和源码对应、11项partial集合与git diff --check复核通过。实现范围已交付，G8/G9的下一步为Lead独立验收及其反馈，其他G/M任务按现有状态登记。
- 原生工具续查记录在 `.local/g8-native-launch-20261111/`。默认、隐藏窗口、脱离控制台、独立进程组配合隐藏窗口四种启动模式下，Ruff版本探针均返回0xC0000142，venv的ctypes探针也均失败。专项 `pytest tests/test_submission.py tests/test_provenance.py -q -p no:cacheprovider` 为37 passed、1 skipped（1.76s）；原生 `ruff check . --no-cache` 与 `ruff format --check . --no-cache` 均退出-1073741502。进程启动模式调整未恢复工具，具体DLL初始化根因待宿主环境诊断。G8/G9继续待Lead独立验收。

- 续跑交接诊断记录在 `.local/g8-runner-handoff-20261111/`。只读核对 `.local/codex-runner/run.ps1` 第7、26、42–45行，任务文本固定，正常退出后等待3分钟再重发，调度分支未按G8/G9待验收状态转交。当前重复续跑因此回到同一交接点，H4调度调整交Lead处理。专项pytest续跑为37 passed、1 skipped（1.73s），原生Ruff check/format均返回0xC0000142。脚本字节与实际命令/退出码已留本机证据，具体DLL初始化根因仍待宿主诊断。

- 现有Linux验证入口续查记录在 `.local/g8-linux-check-20261111/`。`wsl.exe --list --quiet` 退出4294967295并返回 `Wsl/E_ACCESSDENIED`，本轮Linux原生Ruff及隔离构建验证受阻。专项pytest为37 passed、1 skipped（1.71s），Windows原生Ruff check/format均返回0xC0000142。待Lead在可用原生工具环境复验，G8/G9保留待独立验收。
- Lead 验收（2026-11-11）：独立跑全量 411 passed、1 skipped，Ruff check/format 通过，0.4.0 build 成功；用 `artifacts/submission-review-g8-verified/` 打包为 review_only、11 项缺口，`--require-ready` 退出 2；manifest 含 provenance，两组 52 项绑定匹配。G8 改为验收通过。

## G9 · 正式化缺口与退出条件

- 负责人为 root，revision 27，状态为验收通过。写范围为 `data/examples/submission-checklist.json`、`docs/data-contract.md`、`docs/status.md` 和本任务板；不改 H3 的 `.local` 材料生成器，不改精排版 artifacts。
- Lead 预跑：`docs/status.md` 已增加 11 项 review_only 缺口分类表，逐项列出缺什么、责任、可接受证据和退出条件；T3 保持 partial，S.evolution 保持 partial；`--require-ready` 继续拒绝。G8 候选包和本表一起交 04:02 Codex 复核。
- 本轮按官方第3页验证方式核对：T3接受有来源的反事实或三情景论证，退出条件以可复核证据和动作对应为准。方向压力测试可使用显式合成志愿/成绩，容量估计保留来源。研究状态字符串、学校实施批准与未来真实观测分别登记，现有11项partial保持。
- 已提取本机官方PDF第3页核对任务1至4，原文记录留本轮忽略目录。同步T3段落、招生情景与复现退出条件，任务4的概率和影响量估计列为内部完善项。G9表11个唯一ID与源清单partial集合一致，正式拒绝实测通过。剩余11项依赖在status逐项列出，G5/G6的远端复核交Lead安排。
- 续验已补同机全新依赖安装、随包全量测试和已安装CLI的哈希复现记录。C.reproduce继续partial，余下是Lead或其他贡献者的独立验收；G5/G6既有提交基线的远端代码复核已只读核对。当前无其他明确开放、归属本写范围的G/M实现任务，下一步为Lead验收G8/G9及G7图文整合。
- Lead 验收（2026-11-11）：G9 表 11 个唯一 ID 与源清单 partial 集合一致；T3/S.evolution 保持 partial；正式拒绝实测通过；G9 改为验收通过。

## G10 · 展示材料与提交包独立复核

- 负责人为 root，revision 28，状态为下一步。写范围只读：读取 `artifacts/submission-review-r17-polished`、`artifacts/submission-review-g8-verified`、`artifacts/submission-review-g8-verified.zip` 与 `docs/status.md`；复核记录写入 `.local/g10-review-20261111/`。不改 H1–H3 文本/前端/材料生成器，不改 verified 包，不 commit/push。
- 核对：报告 PDF 8 页、答辩 PPTX/PDF 12 页；第 10 页 G7 证据；页脚“strategy-review.json 与 G7 证据”；SMD 0.116、CI [0.027,0.204]；三情景 -0.03 / 0 / 0.058。
- 核对 G8 verified 包：15 个 requirement ID、11 项 partial、manifest provenance、98 项文件、`--require-ready` 退出 2；确认没有把 review_only 写成正式提交。
- 输出 PASS/FAIL、具体不一致项和建议；如无问题写 `no-work.flag`，避免 runner 重复。更新任务板 G10 状态，不自行提交。

## H1 · 文本去防御口癖

- 负责人为 lead，revision 18，状态为验收通过。写范围为 `README.md`、`docs/project.md`、`docs/status.md`、`docs/roadmap.md`、`analysis/competition/RESULTS.md` 以及其他活动 Markdown；不修改 `docs/tasks.md` 的任务事实，不修改源码。RESULTS 防御性短语从 41 处降到 8 处，写作规则已加入 AGENTS；全量测试与链接检查通过。
- 先结论后理由：把重复的“不能/不把/不声称/不得/不进入/不证明”改成正面事实、具体边界或一次集中的限制；保留必要的证据边界，不删未知项，不新增结论。
- 验收为同一事实前后一致；每份文档的限制集中、不反复复述；链接和数字不变；读者能先看到做了什么、结果是什么、还缺什么。

## H2 · HTML 报告前端

- 负责人为 lead，revision 18，状态为验收通过。写范围为 `src/chanjiao_evidence/reporting.py` 的 HTML/CSS 模板；不扩大数据契约，不改报告数值。38 项 reporting/pipeline 测试、Ruff/format 通过，桌面截图检查通过。
- 做一版更清晰的离线报告：报头、关键指标、章节层级、表格和来源区统一视觉；桌面/移动/打印三套布局；只用内联 CSS，不引入外部字体、脚本或网络资源。
- 验收为现有报告内容、转义和链接不丢失；HTML 可离线打开；打印分页合理；相关测试更新并通过；生成样例用于目视检查。

## H3 · PDF/PPT 材料排版

- 负责人为 lead，revision 18，状态为验收通过（精排版预览）。写范围为 `.local/submission-phase-r17/build_polished.py` 及 `artifacts/submission-review-r17-polished`；正式审阅包不改，不改变提交放行条件。PDF 8 页、PPTX 12 页，封面/正文/情景页已渲染检查。
- 复用现有构建器，统一标题、字号、留白、表格、页码和来源注；PDF/PPT 的文字、数字、分母、证据边界与 JSON 一致；不新增无来源结论。
- 验收为 PDF 页数/文字可读、PPT 逐页无溢出、材料清单和哈希重新生成；`review_only` 状态保留，不冒充正式包。

## H4 · Codex 连续运行

- 负责人为 lead，revision 26，状态为 runner 已启动、attempt 1。2026-11-11 04:02:09 启动 `.local/codex-runner/run.ps1`，日志出现 `runner start` / `resume attempt 1`；Codex 在同 thread 上运行，mission 为 G8 复核后接 G9。runner 继续按 quota 30 分钟、正常结束 3 分钟、writer 5 分钟、其他失败 10 分钟重试；04:10 fallback 只检查不重复启动。写范围为 `.local/codex-runner/` 日志与运行状态；不改业务源码和任务板任务事实。
- 用同一 thread `01a1b15b-2a4d-76c1-8b8c-fb2be5c8b100` 的 `codex exec resume` 连续执行任务；每次 quota 后记录错误与恢复时间，恢复后自动续跑，不新开 thread。
- 验收为每次运行有开始/结束/退出码/错误日志；不重复启动同一 Codex 进程；配额恢复后能继续原 thread；Lead 可随时停止并保留未提交改动。

## 当前环境与分工

- Codex（原 thread）：继续 G7 及后续研究/工程，不碰 H1/H2/H3 的写范围，不改 `docs/tasks.md` 的 H 段。
- Lead：H1/H2/H3/H4；每次 Codex 结束先验收，再决定是否提交；配额耗尽时由 H4 负责恢复后 resume。
