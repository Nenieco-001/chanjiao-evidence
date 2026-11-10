# 贡献指南

先读 [项目说明](docs/project.md)、[路线图](docs/roadmap.md)、[当前状态](docs/status.md) 和相关契约，再从 [任务板](docs/tasks.md) 认领有独立验收条件的工作。多 Agent 角色与写范围按 [AGENTS.md](AGENTS.md) 执行。

从最新 main 建立特性分支。一项 PR 处理一个可独立审查的变更，提交信息用中文说明具体行为。接口变化保留既有调用，并记录迁移。用户可见、契约或研究假设变化写入 CHANGELOG 的 Unreleased。

数值测试使用手算或独立推导的预期值，覆盖零效应、负效应、缺失和不可行约束。分析规则先定再跑，保留无优势和资料不足。随机方法记录种子、样本划分、配置与版本，按学校或整个改革安排独立验证。

真实课程记录学校、专业、版本、原始位置与覆盖范围。历史改革记录对象、措施、对照、结果和识别条件。数据保留来源、许可、哈希、清洗和排除规则，原始记录留在本机。新增依赖同步更新开源清单。

```powershell
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m build
```

另跑 README 中受影响的正常入口。数值产物两次运行到新路径并比较，核对 manifest。PR 写明问题、变更、实际命令与结果、研究影响和未验证项。先审查暂存 diff，完成独立验收后由协调者提交并请求 `@codex review`。
