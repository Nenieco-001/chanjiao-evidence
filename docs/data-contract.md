# 数据契约

各命令分别选择自己的 v1 输入类型。公开课程、情景假设、历史面板与招聘数据独立登记，证据含义保留到产物。

## 公开课程与候选情景

`chanjiao curriculum --plan ... --scenario ... --output ...` 读取两份 JSON，写入一个全新目录。课程模式为 published_curriculum，情景模式为 scenario_assumptions，二者均有整数 schema_version=1。

课程输入包含 school、major、program_version、coverage=selected_courses、source 和 courses。source 提供 title、https 原文 url、原文件 sha256 与 location。每门课程提供唯一 course_id、title、credits、hours、semester、prerequisites 和 source_location，数值未公开用 null。周数保留 duration_text，未公开先修写明 prerequisites_status=not_published。

情景包含 label、target_course_id、donor_course_id、hour_options、credit_delta、minimum_hours、minimum_credits、capacity_added_hours、rationale 和 assumption_notes。课程底线与容量是决策假设，单独记录来源与审核需求。

先保留 0 调整原方案，再对正课时选项去重枚举。候选从 donor 转移课时及 credit_delta 学分给 target，检查非负、守恒、底线、容量和已知先修学期。未知关键输入返回 not_evaluable，违反已建模约束返回 infeasible，其余为范围内 feasible。未公开先修与全专业约束列为 unverified_constraints，候选需教师审议。

输出 curriculum-review.json、course-actions.csv、review.md 和 manifest.json。JSON 保存全部候选、约束、生成/评价/反思/修订日志，默认 selected_candidate_id=unchanged。CSV/Markdown 转义外部文字，清单记录实际输入字节、源码与三个结果哈希，已有路径拒绝覆盖。

employment_effect.status 为 unidentified，列出改革、学生结果、对照和迁移证据缺项。目标课时增加作为实践教学投入代理，课程切片可行性与培养效果分别评价。

## 专业要求、修订与机制

`cufe-2025-program.json` 的模式为 published_program_requirements。minimum_total_credits 与 module_minimum_credits 记录原文总学分和十类底线。course_modules 将课程连接到模块，courses 记录第5–6页50门目录及讲课、实验和实践列，空白保留 null。选修池与学生实际选择分别处理，美育及《总则》缺项保留。

`chanjiao strategy --plan ... --program ... --policy ... --evidence ... --effects ... --output ...` 分别读取五份 JSON 字节快照。policy 的模式为 scenario_assumptions，包含 curriculum_scenarios、student_paths、directions、selection_semester、admissions 和 risks。每个课程情景复用已有接口，每条选课路径给出 module_credits 和 selected_course_ids。当前路径是显式构造的情景。检查含调出课、未选调出课和富余学分路径，保留失败；失败触发下一个候选情景的实际重算。

方向配置给出岗位族、关联课程、容量和 [0,1] 范围的成绩门槛。评分仅使用分流前已修的切片课程，等权归一化规则为待审议假设。方向规则包含志愿、同分、容量与未分配处置，未取得学生观测时只输出政策。

admissions 指定原规模、上下界、固定时间窗的就业比例及观测年，未知项为 null。建议相对调幅为 gain 乘观测比例与 target_rate 的差值，经 max_relative_change 限幅和规模上下界检查，再按保守整数规则取整。next_intake_year 等于观测年加 feedback_interval_years，expected_graduation_year 再增加 feedback_lag_years。缺反馈保持原规模并返回 awaiting_inputs。synthetic 模式仅返回合成建议。该模块计算单个调整周期，长期闭环收敛需另行验证。

风险至少三项，按唯一 risk_id、关联 action_id、概率范围、影响、责任、触发和应对登记。概率范围是显式假设，默认 [0,1] 表示未知。专业约束检查通过只覆盖登记路径和条件，学校批准状态为 pending_school_review。

学校实施批准与竞赛材料完备性分别登记。效果验证可采用有来源、可复核的条件情景，真实校内试点和未来观测继续按研究范围标记。

输出 strategy-review.json、review.md、manifest.json。清单登记五份实际输入、所有包源码和两个结果哈希，原子发布并拒绝覆盖。当前入口保留三维差距、资源核定与效果迁移缺项，状态为 review_only。

## 三维条件比较

strategy 可选 `--demand ... --comparison ...`，两项必须同时提供。demand 模式为 historical_sample，包含范围与来源、job_records、skill_counts 和互斥的 job_family_counts。岗位族合计必须等于记录数，每项技能计数不超过记录数。同一岗位可以提及多个技能。

comparison 模式为 scenario_assumptions。skill_links 逐项登记技能、课程ID和原文位置。planned_skills 为拟定课程内容。技能权重分母是词面提及总数，已证实的课程目录文本权重形成覆盖下界，未知内容保留为区间。选修课程可用性与学生实际修读分开。拟定覆盖增量区间以既有证据保留、计划执行且没有覆盖损失为条件，学生掌握效果仍为未识别。

proposed_direction_shares 与 baseline_direction_hypotheses 保留所有岗位族并各自合计1。以总变差距离衡量结构差异，值为对应岗位族比例绝对差之和的一半。比较保留劣于基线、无优势与改善的条件结果，正优势判定用1e-12绝对零容差。实际学校方向分布未取得时，observed_school_gap 保留 null。

scale_scenarios 指定假设届别指数、求职比例、每条记录对应人数与样本可达份额。条件机会为岗位记录数乘每条人数再乘可达份额，条件求职规模为届别指数乘求职比例。输出差额及盈亏平衡可达份额，允许不可达到的阈值大于1。零岗位保留空组及不可识别阈值，实际学校规模缺口为 null。所有乘积与阈值溢出按字段报错。

employment-benchmarks.json 单独登记全国或专业类公开汇总。报告年份、毕业届别、半年后时间窗、指标分母和本机原文位置分别保留，used_for_target_effect 为 false。该卡不自动填充校级就业反馈或把全国值转为校级结果。

## 文献参照的三情景

effects 配置包含目标措施/人群、applicability、唯一 effect_reference，以及 pessimistic/base/optimistic 三项情景。每项的 transfer_factor 在 [0,1] 内，bias 使用原指标单位，assumption_source 说明参数由何处确定。原文标准误存在时用正态近似形成文献参考区间，缺失时仅保留报告点值。

计算值为 transfer_factor 乘报告效应后扣 bias。端点同式计算，保留零、负值与无优势结果。正优势使用 1e-12 绝对零容差，原始浮点值和优势消失阈值保留。支持 log_points 与 proportion_difference。只有 earnings 的对数结果派生相对收入百分比。比例差点值需在 [-1,1]，正态近似区间越界时保留其统计近似含义。

适用性 unverified 或 mismatch 时只给 literature_reference_scenarios，本校效果为 unidentified。人工声明 supported 时也只给 conditional_projection。所有状态的 observed_causal_effect 均为 false。参考区间传播的是论文抽样范围和显式情景，迁移参数未经校准时不构成本校效果置信区间。

## 提交清单与 ZIP

`chanjiao bundle --checklist ... --materials ... --output ...zip` 读取 schema_version=1 的清单。requirements 恰好包含示例中的十五个唯一 ID，status 为 verified、partial 或 missing，note 记录验收内容，evidence 指向包内依据。通过项必须有已列入白名单的依据文件。

files 是显式白名单，每项提供 role、path、permission=public。role 为 report、slides、video、data、source 或 readme。路径使用安全相对路径，拒绝目录逃逸、隐藏目录、原始目录、受限文件、重复路径、符号链接和覆盖。PDF/PPTX 检查文件结构，MP4 检查影片头、画面轨道和时长。时长超过300秒、缺材料、缺依据或任一要求未通过时，包状态为 review_only。`--require-ready` 在这些情况下报错并不发布。

ZIP 使用固定元数据，同一输入生成相同字节。manifest.json 登记实际文件字节、SHA-256、清单字节哈希、视频容器时长、缺项及要求状态。程序核对材料与贡献者登记的结论，科学证据、视觉质量和实际播放由独立审核记录支持。十五项形式与记录通过后状态为 ready，最终赛事模板、报名资格和提交通道另按官方要求核对。

## 历史改革面板

这份文档规定面板 CSV、元数据 JSON 和方案 JSON 必须长什么样，以及产物里有什么。规则按“字段—要求—为什么”列，方便直接对照改数据。

## 面板 CSV

只接受四列，多一列少一列都拒绝。

| 列 | 要求 | 为什么 |
| --- | --- | --- |
| `unit_id` | 非空字符串，读取时去掉首尾空格 | 单位是估计和删除诊断的基本对象，空值或空格差异会让同一个单位对不上。 |
| `year` | 整数 | 后面要按年份取前后两期做差，小数年份会悄悄改变时间窗。 |
| `treated` | 0 或 1，同一单位各年固定；处理组在改革前也记 1 | 处理组身份是分组依据；组别在年份间变动说明数据口径有问题。 |
| `outcome` | `[0,1]` 内的有限比例 | 首版只处理比例指标；`inf`、缺失和越界值会让估计失去意义。 |

面板结构规则：

- 每单位每年一行，不允许重复的 `unit_id`+`year`。重复行会让变化量悄悄重复计权。
- 必须正好覆盖改革前两年和改革当年：`g−2`、`g−1`、`g`。两个改革前年份用来做伪改革检验，少一年就算不出。
- 每个单位三年齐全（平衡面板）。缺一年就取不到前后变化。
- 处理组和对照组各至少 3 个单位。每个单位只有一条变化量，样本太少时区间和删除诊断没有参考价值。
- 首版单位等权，不做规模加权。

## 元数据 JSON

| 字段 | 要求 | 为什么 |
| --- | --- | --- |
| `schema_version` | 整数 `1` | 契约升级后能识别旧文件。 |
| `evidence_mode` | `synthetic` 或 `historical` | 这个标识从输入带到报告，读者能区分合成验证与真实证据。 |
| `outcome_unit` | `proportion` | 首版只接受比例指标，避免百分点和比例混用。 |
| `outcome_id`、`outcome_window`、`population`、`action_id`、`data_license` | 非空字符串 | 报告要能说清指标、时间窗、人群、措施和许可。 |
| `adoption_year` | 整数 | 它是所有时间窗的锚点，也决定面板必须包含哪三年。 |
| `sources` | 非空列表，每项含非空 `title` 和 `url` | 结论要能追到来源。`historical` 模式下 `url` 必须是 https 公开链接。 |

许可和研究适用性要人工核对。格式检查只保证字段存在，不能证明来源可靠、口径正确或数据可用。

多期数据、分期采用、个体级重复记录暂不支持。遇到这类数据，先定研究设计、扩展契约，再改代码和历史材料。保留原始材料；不要为了适配首版删掉不利的年份或单位。

## 方案 JSON

顶层字段：

| 字段 | 要求 | 为什么 |
| --- | --- | --- |
| `outcome_id`、`action_id` | 与面板元数据一致 | 一份估计只对应一个结果指标和一项改革；对不上时算出的“收益”没有意义。 |
| `total_credits` | 正整数 | 学分守恒的比较基准。 |
| `minimum_credits`、`maximum_credits` | 模块最低/最高学分 | 表达培养方案的硬约束。 |
| `budget` | 非负有限成本预算 | 改革不能超出可用资源。 |
| `transfer_factors` | `[0,1]` 非空列表 | 表达“历史效应能迁移多少”的多档假设。 |
| `bias_budget` | `[0,1]` 比例差值 | 给未观测偏差和迁移误差留的扣减额度。 |
| `plans` | 恰两个方案：一个基线、一个改革候选 | 首版只做单项改革比较。 |

单个方案的要求：

- 必须包含 `plan_id`、非负有限数值 `cost` 和 `credits` 对象。基线用 `action_id=null` 标识，也可以省略该键；改革候选必须写 `action_id`。其他字段缺失或类型错误直接拒绝输入。
- `plan_id` 非空且唯一，用于排序和报告。
- 所有方案的 `credits` 模块名完全相同，学分是非负整数。
- 恰有一个基线：`action_id=null`、`cost=0`。其他方案的 `action_id` 与顶层一致。首版只接受一个改革候选，避免把同一个估计分配给不同改革版本。
- 学分和必须等于 `total_credits`。候选方案违反模块最低/最高学分或预算时，报告保留该方案并标 `feasible=false`、列出违规项；基线违反这些约束则报错，否则比较没有参照。

## 方案怎么算

迁移系数（`transfer_factor`）是分析假设，不是估计结果。

- 某方案在某个系数下的增量 = `factor × estimate`。
- 保守增量 = 所有系数下 `factor × ci95_lower − bias_budget` 的最小值。
- 偏差预算在迁移之后扣除，覆盖历史偏差和迁移误差。它是敏感性假设，需要有外部依据。
- 基线的增量恒为 0。可行方案中，保守增量大于 0 才可能被选中；收益相同选成本低的。
- 判据只覆盖当前单一结果指标，不合并就业率、收入、岗位对口等不同指标。

## 产物

`report.json` 保留元数据、估计与诊断、方案比较和研究限制，并新增三年组均值 `trajectory` 与文献背景 `evidence`。`planning` 新增学分变化、资源约束和敏感性格点。数值使用比例原值，HTML 与 Markdown 显示效果时换算为百分点。

`report.html` 与 `report.md` 使用同一份内部结果渲染。HTML 是离线单文件，外部文字会转义，链接仅允许 http/https。没有文献时明确列出缺失输入。

`manifest.json` 包含三个必选输入、可选文献输入的内容哈希，包源码哈希，三个报告的内容哈希，包版本与依赖版本。输入契约 v1 保持兼容，旧命令仍生成新增的可读报告。

哈希使用固定角色名（`panel`、`metadata`、`plans`），提供 `--evidence` 时增加 `evidence`，不写机器路径和运行时刻，这样同一环境相同输入能得到字节一致的产物。manifest 的输入哈希对应实际参与解析的字节，报告和清单不会来自两次不同的读取。跨版本浮点差异用数值测试判断，不靠字节比较。

## 可选文献输入

`--evidence` 读取 schema_version=1 的 JSON，cards 至少一项。每张卡片的 evidence_id 唯一，title、design、source_url、data_status 为非空文字，outcomes 与 transfer_limits 为非空文字列表。source_url 必须为 https 原始来源。现有卡片可保留作者、版本、中文总结、已报道结果和数据获取说明。

系统只按 outcome_id 的精确名称标记 `matches_target_outcome`。同名指标仍需人工核对人群、时间窗和识别设计。`used_for_estimation` 固定为 false，文献结果不自动代入当前面板或改变方案排序。

若提供 reported_results，每项需有 outcome_id、label、interpretation 和 source_location；有 value 时保留 unit，定性结果可省略 value，报告写明未提取数值。source_locations 每项包含 label、url、location 和 version。data_access 为对象，可记录取得状态、材料、申请入口和下一步。缺少可选扩展时仍可读取旧卡片。

## 敏感性格点

后端在输入的迁移系数基础上补充 0、0.25、0.5、0.75、1，在偏差预算基础上补充 0、0.005、0.01、0.02、0.04，去重排序后逐组合比较。每行固定一个系数和预算，保守增量沿用上文公式，资源不可行的候选在所有格点都保留原方案。格点说明选择对假设的依赖。
