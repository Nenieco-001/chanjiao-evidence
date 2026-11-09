# 贡献指南

## 开始

阅读 README、研究规划和相关数据契约，先跑通合成示例。研究任务先说明对象、措施、对照、结果指标、数据与验收条件。涉及假设、接口或依赖路线的决定记录在 `docs/decisions/`。

## 分支与变更

从最新 main 建立 `feat/<topic>`、`fix/<topic>` 或 `docs/<topic>`。一个 PR 处理一个可独立审查的变更。提交前缀使用 feat、fix、docs、test、chore。保留已有调用行为，数据契约变化需说明迁移方式。在 `CHANGELOG.md` 的 Unreleased 记录用户可见或研究假设变化。

## 代码与研究

数值测试使用独立可推导的预期值，覆盖零效应、有害效应、缺失和约束失败。固定选择规则后再分析，保留无优势结果。按学校或整个改革划分开发与验证数据。随机算法记录种子、配置、划分与版本。

论文卡片记录原始来源、对象、措施、结果、识别方法、效应单位、假设与局限。同一试验后续论文标明关联。数据记录 URL、获取日期、哈希、许可、清洗、剔除和口径变化。假设案例明确标 synthetic。

新增依赖同步更新开源清单，说明采用原因。复制或改写代码保留上游版权、固定版本与修改范围。AI 辅助贡献仍需贡献者核验计算、来源与许可。

## 验收与提交

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m build
chanjiao run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --output artifacts/pr-check
```

PR 填写问题、变更、实际验证命令、结果和未验证项。先检查 `git diff --cached` 的公开内容。CI 验证代码与复现，因果识别和外推合理性另行审查。
