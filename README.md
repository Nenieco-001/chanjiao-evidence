# 产教智对 · 历史改革证据与培养方案验证

[![CI](https://github.com/Nenieco-001/chanjiao-evidence/actions/workflows/ci.yml/badge.svg)](https://github.com/Nenieco-001/chanjiao-evidence/actions/workflows/ci.yml)

我们想先搜集学校过去调整培养方案的案例，看看改了什么，学生结果后来有什么变化，再把适用的经验用于新方案。比如假设 A 校在 2010 年增加企业实习，需要结合同期相近专业的变化判断实习带来了多少帮助，并检查这些经验是否适合目标学校。

项目服务北京市大学生“人工智能+”创新大赛第 1 题“产教智对”。主线是把岗位与培养差异转成具体调整，再用历史改革证据约束方案收益及适用范围。

## 首版功能

- 三年平衡面板与指标元数据校验。
- 双重差分、前后对比、改革前伪改革和删除单位诊断。
- statsmodels OLS、HC3 近似区间与明确的识别假设。
- 原方案与单项改革方案比较，检查学分、基础课程底线、实习容量和预算。
- 转移折扣、偏差预算敏感性分析，允许原方案胜出。
- 可重复的 JSON、输入与源码哈希、依赖版本和限制说明。

示例全部为合成数据，用于代码和已知真值验证。真实改革效应需要另行收集和识别。首版提供离散候选筛选，多措施联合优化列为后续任务。

## 快速开始

Python 3.11–3.13。安装需要网络，安装后示例运行离线。命令在仓库根目录执行。

```powershell
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# macOS / Linux 使用 source .venv/bin/activate
python -m pip install -e ".[dev]"
chanjiao run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --output artifacts/example
```

产物为 `report.json` 和 `manifest.json`。输出目录必须为全新路径，防止覆盖已有实验。也可用 `python -m chanjiao_evidence run ...`。

```powershell
# 零效应对照
chanjiao run --panel data/examples/null_panel.csv --metadata data/examples/null_metadata.json --plans data/examples/plans.json --output artifacts/null
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m build
```

`requirements-py313.txt` 记录本次 Windows / Python 3.13 环境的精确版本。其他受支持解释器按 pyproject 解析兼容依赖。

## 继续开发

先读 [研究规划](docs/research-plan.md)、[架构](docs/architecture.md) 和 [数据契约](docs/data-contract.md)，再从 [路线图](docs/roadmap.md) 选择任务。提交遵循 [贡献指南](CONTRIBUTING.md)，协作代理同时遵循 [AGENTS.md](AGENTS.md)。

```text
src/chanjiao_evidence/  数据校验、估计、方案比较、CLI
tests/                 手算、负例、零效应和正常入口测试
data/examples/         合成数据、方案与生成器
data/evidence/         公开论文证据卡片
docs/                  设计、规划、契约与决策记录
.github/               CI、Issue 和 PR 模板
artifacts/             本地产物，Git 忽略
```

## 开源与公开边界

实际统计依赖为 statsmodels，工程组织参考 Cookiecutter Data Science，研究流程借鉴 DoWhy。版本、许可证与借鉴范围见 [开源参考](docs/open-source.md)。原创代码、文档和合成示例采用 MIT，外部论文与数据各自遵循原始授权。

原始数据进入 Git 忽略的 `data/raw/`。可公开数据需核对来源、许可、清洗和统计口径后单独审查。私人邮件、个人信息、凭据和受限数据应留在公开仓库之外。
