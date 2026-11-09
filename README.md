# 产教智对 · 用历史改革证据验证培养方案

[![CI](https://github.com/Nenieco-001/chanjiao-evidence/actions/workflows/ci.yml/badge.svg)](https://github.com/Nenieco-001/chanjiao-evidence/actions/workflows/ci.yml)

先看学校过去调整培养方案时，学生结果发生了什么变化；再用这些变化判断当前方案值不值得改。这是北京市大学生“人工智能+”创新大赛第 1 题“产教智对”的首个可运行版本。

具体到这一版：新增企业实习，是否提高了毕业半年内的就业率？假设 A 校 2010 年增加企业实习，要扣除同期相近专业的变化，才能估计实习本身带来多少帮助。示例数据是合成的，代码和结论都能复现；真实学校的历史效应需要另行收集和识别。

## 现在能做什么

- 校验三年平衡面板和指标元数据：单位、时间窗、来源、`synthetic` / `historical` 标识。
- 估计双重差分（DiD），附改革前伪改革、逐单位删除等诊断。
- 在总学分、基础课最低学分、实习容量和预算约束下，比较“保持原方案”和“一项改革”。
- 用迁移系数和偏差预算做敏感性分析；证据不足时保留原方案。
- 输出 JSON 报告、输入/源码哈希和依赖版本；相同输入结果一致。

示例数据只用来验证代码和已知真值。真实就业率、收入、岗位对口和任务能力的效应要分别测量，学校层面的就业率不能替代学生能力。

## 快速开始

需要 Python 3.11–3.13。安装要联网，安装后示例离线可跑。以下命令在仓库根目录执行。

```powershell
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate
python -m pip install -e ".[dev]"

chanjiao run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --output artifacts/example
```

得到 `artifacts/example/report.json` 和 `manifest.json`。正效应示例的估计约为 0.04（4 个百分点），选中 `internship`；零效应示例选中 `unchanged`。输出目录必须是新路径，防止覆盖旧实验；重跑时换个新目录。也可以直接跑 `python -m chanjiao_evidence run ...`。

再跑零效应对照、测试和打包：

```powershell
chanjiao run --panel data/examples/null_panel.csv --metadata data/examples/null_metadata.json --plans data/examples/plans.json --output artifacts/null
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m build
```

`requirements-py313.txt` 是本次 Windows / Python 3.13 环境的精确版本，其他受支持解释器按 `pyproject.toml` 解析依赖。

## 目录

```text
src/chanjiao_evidence/  数据校验、估计、方案比较、CLI
tests/                  手算、负例、零效应和正常入口测试
data/examples/          合成数据、方案与生成器
data/evidence/          公开论文证据卡片
docs/                   设计、规划、契约与决策记录
.github/                CI、Issue 和 PR 模板
artifacts/              本地产物，Git 忽略
```

## 继续开发

先读 [研究规划](docs/research-plan.md)、[设计](docs/design.md) 和 [数据契约](docs/data-contract.md)，再从 [路线图](docs/roadmap.md) 挑任务。已做的核验见 [核验记录](docs/verification.md)。提交遵循 [贡献指南](CONTRIBUTING.md)；多个 agent 协作时按 [AGENTS.md](AGENTS.md) 分工。

## 开源与公开边界

统计依赖是 statsmodels，工程组织参考 Cookiecutter Data Science，研究流程借鉴 DoWhy，版本和许可证见 [开源参考](docs/open-source.md)。原创代码、文档和合成示例用 MIT，外部论文与数据遵循各自授权。

原始数据放在 Git 忽略的 `data/raw/`。可公开的数据要先核对来源、许可、清洗和统计口径；私人邮件、个人信息、凭据和受限数据不要进公开仓库。
