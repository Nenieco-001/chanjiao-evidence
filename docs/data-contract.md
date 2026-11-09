# 数据契约 v1

## 面板与元数据

CSV 只接受 `unit_id,year,treated,outcome` 四列。unit_id 为非空字符串，year 为整数，treated 为固定组身份 0/1，处理组改革前也为 1。outcome 为 [0,1] 有限比例。共同改革年份为 g，只接受 g−2、g−1、g 三年平衡面板，每单位每年一行，至少三个处理与三个对照单位。首版单位等权。

JSON 的 schema_version 为整数 1，evidence_mode 为 synthetic 或 historical，outcome_unit 为 proportion。outcome_id、outcome_window、population、action_id、data_license 为非空字符串，adoption_year 为整数。sources 为非空列表，每项有 title 和 url，历史来源必须为 https。许可和研究适用性需人工核验，格式检查只保证字段存在。

有多期、分期采用或个体重复记录时，先另行确定设计并扩展契约。保留原始材料，不通过删除不利时期适配首版。

## 方案

顶层包含 outcome_id、action_id、total_credits、minimum_credits、maximum_credits、budget、transfer_factors、bias_budget 和 plans。行动和结果指标须与面板元数据一致。

每个方案有唯一 plan_id、action_id、非负有限 cost 和 credits 字典。学分为非负整数，各方案模块相同。恰有一个 action_id=null、cost=0 的基线，其他方案 action_id 与顶层一致。首版只接受一个改革候选，避免将同一个估计分配给不同改革版本。

学分和等于 total_credits，遵守模块最低与最高学分及成本预算，基线也须可行。transfer_factors 为 [0,1] 非空列表，bias_budget 为 [0,1] 比例差值。

场景增量为 factor × estimate。保守增量取所有 factor × ci95_lower − bias_budget 的最小值。偏差预算在转移后扣除，表达历史偏差与迁移误差的敏感性假设。基线增量为零，相同收益优先低成本。该判据仅覆盖当前单一结果指标。

## 产物

report.json 保存元数据、估计与诊断、方案比较和限制。manifest.json 保存三个输入内容、包源码、报告哈希及环境版本。使用固定角色名，避免机器路径和时刻影响确定性。同一环境相同输入输出字节一致，跨版本浮点差异用数值测试判断。
