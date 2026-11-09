# 合成示例

16 个虚构专业单位，每组 8 个，三年数据。生成公式包含组间基础差异、分布相同的单位趋势和 2022 年共同改革效应。正效应设为 0.04，即 4 个百分点，零效应设为 0。所有学分、成本、迁移系数和偏差预算也为合成假设。

估计函数只读取面板结果与改革年份，不读取 known_synthetic_effect。该字段用于核验已知真值。示例不能代替真实改革材料。

```powershell
python data/examples/generate.py --output data/examples
```

重新生成后应与当前 CSV 和 JSON 一致。提交前运行测试和 git diff，确认更改是否符合生成规则。
