# 首版实施计划

> 本计划在当前会话内依次执行。实现变更需同步测试、数据契约和变更记录。

## 目标与约束

交付可安装、可复现、可协作开发的历史改革验证基础工程。Python 3.11–3.13，statsmodels 0.15.0，默认离线运行，示例只使用合成数据，公开仓库保留数据来源与许可证边界。

## 执行清单

- [x] 建立 src 布局、包元数据、开发依赖、忽略规则与 CI。
- [x] 先写数据与估计测试，运行失败记录，再实现面板校验和 DiD。
- [x] 先写方案比较测试，再实现学分、预算、容量约束和原方案对照。
- [x] 先写 CLI 测试，再实现输入输出、确定性报告和哈希清单。
- [x] 提供合成生成器、零效应对照和公开论文证据目录。
- [x] 编写研究规划、架构、贡献指南、AGENTS、变更记录与开源引用。
- [x] 本地运行测试、ruff、wheel 构建、正常 CLI 与零效应 CLI。
- [ ] 将已验证文件提交公开仓库，核验远端内容和 CI 状态。

## 接口

`load_panel(csv_path, metadata_path)` 返回校验后的 DataFrame 与元数据。

`analyze_panel(frame, adoption_year)` 返回主估计、改革前伪改革与删除单位诊断。估计单位为比例差值，0.01 对应 1 个百分点。

`compare_plans(config, effect)` 返回每个完整方案的可行性、资源约束与效果敏感性排序。使用主估计的区间和显式偏差预算，不自动合并不同结果指标。

`run(panel_path, metadata_path, plans_path, output_dir)` 校验全部输入后原子提交一个全新产物目录。失败时清理本次临时目录，保留已有产物。

## 本地验收命令

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m build
chanjiao run --panel data/examples/panel.csv --metadata data/examples/metadata.json --plans data/examples/plans.json --output artifacts/example
chanjiao run --panel data/examples/null_panel.csv --metadata data/examples/null_metadata.json --plans data/examples/plans.json --output artifacts/null
```
