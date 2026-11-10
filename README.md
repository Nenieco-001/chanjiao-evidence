# 产教智对

项目研究怎样调整一个真实本科专业的培养方案，以及怎样在没有线下试点时论证调整效果。需求分析提供线索，课程与资源决定动作，历史改革证据约束效果范围。

## 当前重点

当前已具备本地招聘数据处理、限定需求画像、回顾性回测及合成改革基线。工作重心已转回真实培养方案、具体课程动作和可信验证。公开课程切片与情景假设分别输入，计算得到的可行性仅覆盖建模范围，就业效果缺证据时保持未识别。

## 全局文档

- [项目说明](docs/project.md) 定义目标、赛题要求、研究问题和证据口径。
- [路线图](docs/roadmap.md) 定义推进顺序、产出和验收条件。
- [状态与偏移](docs/status.md) 记录当前能力、缺口及纠偏结果。
- [唯一任务板](docs/tasks.md) 记录任务负责人、版本、范围和状态。
- [数据契约](docs/data-contract.md) 定义各入口输入与产物。
- [架构](docs/architecture.md) 说明实际模块和运行关系。
- [开源引用](docs/open-source.md) 记录依赖、许可证和借鉴范围。

协作遵循 [AGENTS.md](AGENTS.md) 和 [贡献指南](CONTRIBUTING.md)。历史留言与交付草稿移出活动文档，已完成需求分析保存在 [分析结果](analysis/competition/RESULTS.md)，运行方法见该模块 [README](analysis/competition/README.md)。

## 安装

Python 3.11–3.13。安装后默认离线运行。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## 真实课程切片

```powershell
chanjiao curriculum --plan data/curricula/official-cs-extract.json --scenario data/examples/curriculum-scenario.json --output artifacts/curriculum-review
```

公开课程输入保留原始出处，情景文件单独标记决策假设。输出课程动作、约束检查、生成与修订日志，以及效果证据缺项。默认保留原方案，候选供教师审议。完整培养方案与资源核定仍需补齐。

## 已有研究基线

```powershell
chanjiao run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --evidence data/evidence/internships.json --output artifacts/causal-example
```

该示例使用合成学校面板，验证 DiD 与方案比较实现。文献作为背景单独展示。

## 本地大数据

```powershell
chanjiao warehouse ingest --csv .local/input/jobs.csv --database .local/warehouse/jobs.duckdb --dataset-id campus-jobs --version annual-2026 --expected-year 2026 --output .local/warehouse/import.json
chanjiao warehouse summary --database .local/warehouse/jobs.duckdb --dataset-id campus-jobs --version annual-2026 --limit 10 --output .local/warehouse/summary.json
```

替换实际输入路径，每个报告使用新路径。完整子命令由 `chanjiao warehouse --help` 查看。原始文件、数据库、描述、定位和个人级记录留在本机，LLM 读取字段、质量计数和有上限的聚合。各数据版本单独查询。

## 验收

```powershell
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m build
```

运行通过说明代码和复现流程可检查。学生能力、就业和改革收益的结论按项目说明的研究标准独立验收。
