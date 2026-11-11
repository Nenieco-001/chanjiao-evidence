# 计算机专业需求侧工作台

本目录把本机招聘切片转成可复核的年份内结构，不扩展现有平台。
报告及证据边界统一见 [分析报告](RESULTS.md)。
任务、写范围与验收状态见 [唯一任务板](../../docs/tasks.md)。

## 输入与依赖

- Python 3.11–3.13，仅标准库；运行分析不需要 pandas、DuckDB、LLM、网络或安装新包。
- 输入用 `--input-dir` 显式指定年度 CSV 目录，文件名为 `上市公司招聘数据<年份>.csv`。
  既有运行使用2016/2023/2026三个完整年度成员，合计约1.10 GB；回测另使用2024/2025年度成员。
  原包与原始CSV放在使用者自己的只读数据目录，输出和提取记录另选目录。
- 官方数据字典已于2026-11-11取得，规则见 [官方材料摘要](OFFICIAL-MATERIALS.md)。本轮仅从本机RAR读取表头，核对全量24列与2022单年23列，后者缺「来源平台」。两种表头都包含工作台必需的14列，当前代码使用「来源」，读取不依赖「来源平台」。
- 合成fixture已验证24/23列表头及重排列序下的读取与汇总。2022年度仍在工作台年份白名单之外，`--years 2022` 会被拒绝；其类别语义尚待审计。仓库导入入口已用2022合成记录验证23/24列兼容。
- 使用 UTF-8/BOM 和真正的 CSV 解析器，支持描述内换行。按列名读取，
  允许一个末尾空列；非空尾列记录单列计数并排除，损坏记录、缺字段报错。
- 长字段读取上限提高至至少2³¹−1字符，已有更高进程设置沿用。日期去首尾空白后按ISO日期解析，年度接受整数或尾部`.0...`，职位描述保留原文以核对字符跨度。
- 脚本、课程占位示例及输入哈希写入产物；输入哈希只读计算。
  输入只读，必须在两次运行之间保持不变。
- `tests/test_competition_analysis.py` 依赖项目已有 pytest；全仓测试还会加载现有统计依赖。
- `tests/test_official_recruitment_schema.py` 覆盖官方表头与清洗边界。股票代码`000001`经仓库CSV导入、VARCHAR存储及Parquet导出后保留前导零，仓库测试使用DuckDB。
- 当前按招聘记录计数，招聘人数保留原字符串。「若干」「3人」「0002」和空值只验证可读及岗位分母；人数数值解析与人数加权另需实现。统一社会信用代码、行政区划代码属于其他数据结构，当前工作台未消费，本轮测试不覆盖其清洗或对齐。

## 运行

从仓库根目录执行，先把占位符替换为本机目录。下列输出子目录必须尚不存在。

```powershell
$inputDir = '<ANNUAL_CSV_DIR>'
$outputRoot = '<OUTPUT_ROOT>'
python analysis/competition/workbench.py --input-dir $inputDir --output (Join-Path $outputRoot 'run-01')
python analysis/competition/workbench.py --input-dir $inputDir --output (Join-Path $outputRoot 'run-02')
# 只复现一个年度，仍使用同一口径
python analysis/competition/workbench.py --input-dir $inputDir --years 2026 --output (Join-Path $outputRoot 'year-2026')
python -m pytest -q tests/test_competition_analysis.py tests/test_official_recruitment_schema.py
```

可用 `--input-dir` 指向其他只读年度 CSV 目录。2024/2025 已逐年核对表头、类别常见值、
来源、日期、缺失和目标切片重复；采用各自的显式语义映射，不沿用 2026 的类别解释。
同名字段仍按独立的上市公司行业/岗位名称筛选，类别列不用于筛选或训练。
不支持合并应届生数据；其行业列缺失、总体不同。
命令向终端只打印输出目录和入选数，不打印描述、企业或联系方式。
每次先写同父目录的临时目录，完整后原子改名；拒绝覆盖，失败清理本次临时目录。

比较两次结果（含 manifest，共 11 个文件）：

```powershell
$a = Join-Path $outputRoot 'run-01'
$b = Join-Path $outputRoot 'run-02'
$different = @(Get-ChildItem -LiteralPath $a -File | Where-Object {
  (Get-FileHash -LiteralPath $_.FullName).Hash -ne
  (Get-FileHash -LiteralPath (Join-Path $b $_.Name)).Hash
})
if ($different.Count) { throw '产物不一致，请核对输入和脚本版本' }
```

运行结果和本机 DLL 替代入口见报告的“运行证据”。不改全局 Python 配置。

### 2024/2025 回顾性回测

先用已有仓库接口提取两个明确成员，通过`--archive`和`--unrar`传入归档与已安装解压程序。
占位目录可使用绝对路径，原始CSV和提取元数据留在使用者的私有目录。若选用仓库内目录，应登记Git忽略规则。以下输出文件均须尚不存在。

```powershell
$archivePath = '<ANNUAL_RAR_ARCHIVE>'
$unrarPath = '<UNRAR_EXECUTABLE>'
$backtestDir = '<BACKTEST_CSV_DIR>'
$metadataDir = '<PRIVATE_METADATA_DIR>'
python -m chanjiao_evidence warehouse unpack --archive $archivePath --member '上市公司招聘数据2024.csv' --unrar $unrarPath --destination (Join-Path $backtestDir '上市公司招聘数据2024.csv') --output (Join-Path $metadataDir 'extract-2024.json')
python -m chanjiao_evidence warehouse unpack --archive $archivePath --member '上市公司招聘数据2025.csv' --unrar $unrarPath --destination (Join-Path $backtestDir '上市公司招聘数据2025.csv') --output (Join-Path $metadataDir 'extract-2025.json')
python analysis/competition/workbench.py --input-dir $inputDir --years 2016 2023 2024 2025 --annual-input-dir $backtestDir --backtest --output (Join-Path $outputRoot 'backtest-01')
python analysis/competition/workbench.py --input-dir $inputDir --years 2016 2023 2024 2025 --annual-input-dir $backtestDir --backtest --output (Join-Path $outputRoot 'backtest-02')
```

`--backtest` 要求 2023/2024/2025，2016 可选；默认不启用，三个年度画像仍输出 11 文件。
回测例生成 13 文件：四个年度图，原有聚合及新增 `backtest.json`，均写入 manifest 哈希。
2024 只用可用的 2016/2023，2025 只用 2016/2023/2024；没有补齐的年份不假装存在。
2026 即便输入也不参与预测，但它已影响词表设计，评价属于回顾性回测。

`backtest.json` 分两市合计、北京、上海列实际画像、预测值和两种固定方法：
`latest_year` 保持最近年度；`annual_mean` 对截止年内可用年度的比例等权平均，
薪资预测为有效年度中位数的均值。空训练年度不补零，实际空样本的误差为 null。
岗位族固定五类，MAE 为五项份额绝对差的均值，TVD 为五项绝对差之和的一半；
技能以全部去重岗位为分母，MAE 覆盖全部 12 词，零提及保留为 0。
Top-5 只排正提及率，并列按技能名排序；重叠数除以 5，即便不足五项也不改分母。
薪资误差为报价区间中点中位数的绝对差及除以实际中位数的相对差，同时列实际有效区间覆盖率。
`improves_baseline` 逐指标按严格小于最近年度基线判定，相同或更差均为 false。
该开关只比较未经来源/月度匹配的年度原切片，没有把误差当作真实培养效果。

### 共同支持切片与误差组

第 4 批在原有去重后，增加可选的回顾性诊断；包含原全年 `backtest.json`，
不替换全年对照。下列两个输出目录必须为新路径：

```powershell
python analysis/competition/workbench.py --input-dir $inputDir --years 2016 2023 2024 2025 --annual-input-dir $backtestDir --matched-backtest --output (Join-Path $outputRoot 'matched-01')
python analysis/competition/workbench.py --input-dir $inputDir --years 2016 2023 2024 2025 --annual-input-dir $backtestDir --matched-backtest --output (Join-Path $outputRoot 'matched-02')
```

新增 `matched-backtest.json`，这组四年输入共生成 14 个文件。
按平台标签、月份、城市、上市公司行业、学历、经验的顺序，取**每个训练年和目标年**的共同值，
每层都在上一层保留的样本中重新取交集；最后要求六维完整组合也共同出现。
不是把训练年度合并后只要有一次出现就接受，也不是只检查各字段的边际重合。
月份使用各年共同出现的月份，具体窗口写入 `stages`，不自动称为 1–3 月同期。
每年仍保留切片内部原权重，未平衡平台、月份或完整组合的样本数。

`original_samples` 记录各年原切片 n 及六个字段缺失；`stages` 逐层列共同值/数量、
各年 before_n、剩余 n、相对原切片的 coverage、相对上一层的 retention、当前及原切片缺失数。
某层没有共同值时，`status=no_common_support`、`stopped_at` 写明断层，
未执行层写入 `unreached_layers`，匹配评分全部为 null。不会用全年误差填补。
平台空值与 NA/null 等缺失标记不视为同源；学历缺失/未映射不算支持。
经验按去首尾空白后的原文精确匹配，不把“3-5年”和“3至5年”强行合并。
匿名平台同号尚未确认真实身份，本轮匹配以同号可比为条件。

`groups` 按城市、行业、平台、学历、经验枚举原切片各年取值并集，额外保留固定城市/行业。
每组列目标 n、原组 n、组内保留覆盖率、在匹配总样本中的占比、各训练年画像、描述与薪资覆盖，
以及岗位族 MAE/TVD、技能 MAE/Top-5、薪资绝对/相对误差。
分组两个方法均要求每个训练年和目标年非空；缺一年的组保留并标无支持，不借其他组补分数。
`full_year.groups` 给同口径的全年分组对照，原全年方法仍在 `backtest.json`。
原组 n=0 时 coverage 为 null；原组非空、匹配后为空时 coverage=0。
任一年 n<30 标 `small_sample=true`，仅作描述提示，不是显著性检验。
Top-5 改善按重叠率严格大于基线，误差类指标按严格小于；零命中、相同与更差均保留。

`leakage` 只输出跨年企业同名、同企业+岗位原名+城市的目标记录重叠数/率及缺键数；
不输出企业、岗位文本或散列标识，不把疑似重复当确认转发，也不自动剔除重复企业。
匹配选择使用了目标年协变量，2026 又参与过词表探索，因此只能作回顾性描述。
实际样本、误差、泄漏数字与不可下的结论统一见 [分析报告](RESULTS.md)。

## 固定分析口径

目标为计算机科学与技术，地区仅北京、上海（只去掉末尾“市”），行业只接受
`上市公司行业` 中的“计算机、通信和其他电子设备制造业”“软件和信息技术服务业”。
这列描述上市公司的行业，不能认定每个子公司或岗位实际所属行业。
按岗位名称归入软件开发、软件测试、算法与机器学习、数据分析与工程、系统运维与安全；
先排除销售、招聘、猎头、硬件、电气、机械、工艺、生产、采购词面。
它是保守岗位族代理，会漏掉通用“开发工程师”，也可能纳入技术支持等邻近职位。
数据没有专业字段，不声称精确匹配目标专业，也不把全体岗位叫“应届生岗位”。

要求发布年份可精确写成年度或 `.0...`，发布日期可解析且在该年内；
2026 截止 3 月 10 日。异常行保留计数。结束日期不决定窗口。
在每个年度目标切片内，按企业原文、岗位原文、归一化城市、发布日期、
薪资上下限原文去重，保留先出现的行。不同平台同键也合并；描述不同仍保留首条，
可能损失技能证据。企业缺失时不合并，单列计数。这是近似去重，不是唯一职位 ID。
不按招聘人数加权，不相加跨年记录数，不推断招聘总量趋势或全国人才缺口。

技能采用 12 个在实际描述探查中出现的具体词面，定义在 `SKILLS`；
不是引用或伪造的标准技能词典，不把 SQL 与数据库等宽泛概念强行合并。
英文忽略大小写，用 ASCII 字母/数字边界避免 Java→JavaScript、Git→digital 误报；
因此 MySQL 不计 SQL，未收录同义表达会漏报。中文逐字匹配。
有限否定规则只检查同分句命中前 12 字中的“无需/不要求/不需要/不必”。
“不熟悉 Python 也可培训”、福利中的技能名等仍可能误判；只报告“提及”，不报告“必备能力”。
每岗位每技能最多计一次，多标签占比和可以大于 1。
同时给出全部去重岗位分母和非缺失描述分母；空样本比例留空/null，零命中保留 0。

薪资仅接受上下限为有限数且 `0 < 下限 <= 上限` 的月薪区间。
中位数与四分位数针对**区间中点**，分箱也用中点；四分位数为线性插值。
0与空月薪均作为未标明报价排除，原始文本空缺率和有效薪资覆盖率分别保留。
不补薪数、奖金、工时或通胀。产物按“最低/最高月薪”标示元/月，币种和薪数等平台细节随来源核对。
它是各经验层次的报价，学生起薪另需毕业生观测。
学历映射保留缺失、未明确和其他，经验只保留原类目，避免跨年等义假设。

## 产物与复核

- `summary.json`：historical 标识、输入哈希、记录数、过滤/重复数、日期范围、
  全年度与目标切片字段缺失数/率、来源分布、分年类别语义与常见值。
- `structures.csv`：岗位族/城市/上市公司行业/学历/经验/月薪中点分箱；每行保留 n、分母与比例。
- `skills.csv`：分年度、两市合计及各城市的全部词表（含零命中）和两个分母。
- `salary.csv`：每个分组的有效/无效区间数及中点 p25/median/p75。
- `skills-2016.svg`、`skills-2023.svg`、`skills-2026.svg`：各年独立的 Top-8 提及率图，
  横轴均按 0–100% 比例尺，不连成跨年趋势图。
- `skill-evidence-local.json`：每年度每技能接受/拒绝各至多两条，
  记录 CSV **数据记录序号**（不含表头，区别于物理行号）、词面、字符跨度和规则理由。
  不复制原始企业、地址、联系方式或完整描述。用输入哈希核对文件，再按记录和跨度本机回查。
  这些是程序证据定位，未人工标注，不是抽取准确率评测。
- `rules.json`：规则与合成命中、误判、否定反例；不会伪装成独立真实评测集。
- `gap-example.json`：historical 需求词面与 synthetic 课程占位的集合差演示。
- `manifest.json`：输出哈希、脚本与课程占位哈希，不带时间戳或输出绝对路径。

`artifacts/` 整体被 Git 忽略，所有本机结果仍留在本机。
证据定位文件不得强制加入 Git；其余聚合是否可公开由协调者核对许可后决定。

## 课程接口

[`curriculum.schema.json`](curriculum.schema.json) 是文档 schema，
[`curriculum-placeholder.json`](curriculum-placeholder.json) 是明确标为“示例占位”的合成输入，
没有真实学校。脚本仅对实际使用的学时与技能字段做边界检查，不声称已运行完整 JSON Schema 校验器。
`curriculum_gap(plan, demand)` 是最小接口，仅返回词面集合的覆盖/未覆盖。
默认使用本次最早输入年度需求进行接口演示；有提及的词才进入差集。
比例与学时单位不同，不相减、不生成删课建议、不外推学生能力。
接真实学校前应补齐来源、版本、许可、课程目标定位、师资/学分/先修/容量及教师复核，另升级契约。
