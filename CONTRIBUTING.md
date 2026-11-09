# 贡献指南

## 开始

先读 README、研究规划和数据契约，跑通合成示例。研究任务先说清对象、措施、对照、结果指标、数据和验收标准。涉及假设、接口或依赖路线的决定记到 `docs/decisions/`。

多个 agent 为同一个人工作时，按 [AGENTS.md](AGENTS.md) 划分角色、任务和写范围；对外只有协调者提交，只留一套结论。

## 分支与变更

从最新 main 开 `feat/<topic>`、`fix/<topic>` 或 `docs/<topic>`。一个 PR 只做一件可以独立审查的事。提交前缀用 feat、fix、docs、test、chore。数据契约变了要说明迁移方式，并在 `CHANGELOG.md` 的 Unreleased 记一条。

## 代码与研究

- 数值测试用能独立推导的预期值，覆盖零效应、负效应、缺失和约束失败。
- 改变行为先写会失败的测试，再实现。
- 分析规则先定后跑；无优势、无法识别、资料不足的结果照样保留。
- 按学校或整个改革划分开发与验证数据；随机算法记录种子、配置、划分和版本。
- 论文卡片写明来源、对象、措施、结果、识别方法、效应单位、假设和局限。
- 数据记录 URL、获取日期、哈希、许可、清洗和口径。
- 新增依赖同步更新 `docs/open-source.md`，说明为什么加。
- AI 辅助的贡献由人类贡献者核验计算、来源和许可。

## 验收与提交

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m build
chanjiao run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --output artifacts/pr-check
```

PR 写清问题、改了什么、实际跑了哪些命令、结果和没验证的部分。先看 `git diff --cached` 有没有不该公开的内容。CI 管代码和复现；因果识别和外推合理性要人工审查。
