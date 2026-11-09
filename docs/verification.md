# 核验记录

这份文档记录 2026-11-09 在 Windows / Python 3.13.7 上实际跑过什么、结果是什么。精确依赖见 `requirements-py313.txt`。首版记录对应提交 a14e06a；去过度防御复验对应 0.2.0 之前的工作区；0.2.0 记录对应当前 `feat/analysis-workbench` 工作区，见下文。核验使用公开合成示例，真实历史面板尚未取得。

## 已运行

- `python -m pip install -e ".[dev]"` 成功。
- `python -m pytest -q`：34 项通过，覆盖面板校验、手算 DiD、零效应、有害效应、伪改革、资源约束、指标对应、覆盖保护和 CLI 退出码。
- `python -m ruff check .` 与 `python -m ruff format --check .` 通过。
- 生成器设定的效应为 0.04；估计为 0.04（4 个百分点），近似区间 [0.03588924, 0.04411076]。
- 零效应示例在浮点精度内为 0，原方案被选中。正效应和零效应两个示例的改革前伪改革都在浮点精度内为 0。
- 相同输入运行两次，报告相等，`manifest.json` 字节相同。
- sdist 与 wheel 构建成功。wheel 安装到独立目录后，在源码目录之外跑正常 CLI 成功，确认导入的是安装包。sdist 包含 conftest、示例数据和研究文档，解压后的测试同样 34 项通过。
- 生成器重新生成五个示例文件后字节一致；三个实际运行产物的报告哈希核对通过。

## 去过度防御改动后的复验

2026-11-09，在同一环境对提交前的最终工作区复跑（改动包括输入只读一次、解析与哈希共用同一份字节）：

- `pytest` 38 项通过（原 34 项，新增清单输入哈希、方案 JSON 非对象和基线不可行用例）；`ruff check` 和 `ruff format --check` 通过。
- 离线构建成功（`python -m build --no-isolation`，使用本机缓存的 setuptools）。隔离构建需要访问 PyPI，当前环境网络不可用，未验证。
- 正效应与零效应示例重跑，`report.json` 与改动前逐字节一致；相同输入两次运行，报告和清单字节一致。
- 清单里的三个输入哈希与各自输入文件字节一致，解析和哈希使用同一份读取结果。
- 方案 JSON 为 `[]` 或 `null` 时以退出码 2 拒绝，提示“plans JSON must be an object”，不生成产物。
- 对已存在输出目录重跑仍以退出码 2 拒绝，原目录内容不变，没有暂存目录残留。
- 面板、元数据和方案配置的边界拒绝路径全部保留，测试覆盖未减少。

## 0.2.0 · 中文报告与文献证据

2026-11-09，对 `feat/analysis-workbench` 工作区做独立验收（提交前状态）：

- `pytest -q`：85 项通过（原 83 项，新增 Windows 发布重试与 HTML 标题用例）。
- `ruff check .` 与 `ruff format --check .` 通过。
- 离线构建：0.2.0 sdist 与 wheel 成功；隔离构建因本机访问 PyPI 超时未验证。
- CLI 带/不带 `--evidence` 均生成 `report.json`、`report.html`、`report.md` 和 `manifest.json`；带文献时 manifest 输入多一项 `evidence` 哈希；四份产物哈希与实际文件一致；相同输入两次运行字节一致。
- 带与不带文献的 `analysis`、`planning`、`trajectory`、`limitations` 相同，只有 `evidence` 与 manifest 输入不同；`used_for_estimation=false`，两张卡片当前 `matches_target_outcome=false`。
- HTML 无 script、link、svg 等外部资源，外部文本转义，链接仅 http/https；Markdown 无原始 HTML 或危险链接；已存在输出目录重跑 exit 2，产物不变。
- CLI 在 `PYTHONIOENCODING=cp1252` 的模拟旧版 Windows 输出下以 0 退出，中文提示不再触发 `UnicodeEncodeError`。
- 独立复算 DiD 0.04、credit_changes 与 25 格 sensitivity 公式；证据卡片结构与 `docs/evidence-findings.md` 数值一致。
- 已知环境限制：本机默认 TEMP 不可写时 pytest 会回退到仓库根生成临时目录，已在 `.gitignore` 忽略；全量测试曾偶发 Windows 发布 `os.rename` PermissionError，现已对 winerror 5/32 做有上限退避重试并补回归用例。

## 持续核验

提交 c93b3c7 在 Windows、Linux 和 Python 3.11、3.13 四组 CI 均通过，包含安装、测试、静态检查、构建和两个 CLI 示例。[首次远端核验](https://github.com/Nenieco-001/chanjiao-evidence/actions/runs/42586502611)

后续状态以 Actions 实际记录为准。CI 只能证明代码和复现流程；研究识别与外推合理性、数据许可要人工审查，不能由 CI 代劳。
