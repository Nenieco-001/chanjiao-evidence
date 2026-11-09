# 本地数据仓库

## 这轮先完成什么

把招聘原始数据交给本地程序和 SQL 引擎处理，LLM 读取字段、质量计数及限定数量的汇总。先核对重复 ZIP，再跑通一个实际年度的完整入库，保留版本与异常记录。

原始 RAR/ZIP 留在原目录。DuckDB 保存本地可查询数据与导入登记，Parquet 按指定数据集和版本导出，作为后续批量分析交换格式。数据量增长后按年份组织文件。数据库、原始记录与导出文件放在 Git 忽略目录。

## 为什么采用 DuckDB

当前工作是单机批量读取、筛选和聚合。DuckDB 提供嵌入式持久化 SQL、CSV/Parquet 读写和磁盘溢写，可以设置内存和线程。首版固定 2.0.0，默认 512MB 和两个线程。内存限制并非整个进程的严格上限，复杂分组和排序仍需留磁盘和内存余量。[Python 接口](https://duckdb.org/docs/2.0/clients/python/overview) · [大于内存的处理](https://duckdb.org/docs/2.0/guides/performance/how_to_tune_workloads)

## 版本与质量

文件完整性、不同副本内容是否相同、字段质量和研究适用性分开检查。ZIP 的 CRC 和成员 SHA-256 能发现损坏和内容差异，不能证明政策或数字本身正确。RAR 先列目录，按明确成员提取，完成后核对进程退出码和实际输出哈希。

总表、分年 CSV 和 DTA 视为候选表示，登记数据集、版本、来源路径及内容哈希。每个版本单独入库和查询。同版本同内容重试不增加数据，不同内容要求改版本名。字段保留原始文字，类型化视图与质量计数指出缺失、薪资转换、日期和重复问题。

实际招聘总表有 20/24 列，分年版可能缺少来源平台，形成 19/23 列变体。该列按已知可选字段补 NULL，登记实际原始列和 missing_optional_columns，并在质量报告计入缺失。其他必需字段和未知字段继续在入口核对。

四位年份可使用整数或尾部全为零的小数形式，例如 2026、2026.0、2026.00。类型化结果取精确整数，原文保持原样，normalization_counts 记录转换数量。2026.5 等分数年份继续计为异常。日期按 YYYY-MM-DD 解析。

同内容幂等重跑也会刷新类型化视图，适用于清洗规则升级后的已有数据库。原始记录和登记数量不变。已有 Parquet 为导出时的快照，更新规则后应导出到新路径。

不凭副本名称自动判定可信。用户提供的可靠副本线索与程序检查结果都记录，存在冲突时保留两方来源。

## LLM 接口边界

默认只输出字段说明、完整性结果、计数、日期范围及 Top-N 汇总，N 为 1–50。原始职位描述、个人联系方式和整表留在本机。模型需要解释趋势时，由程序先执行固定 SQL，报告标出范围、版本和质量计数。

原有培养改革分析继续使用学校或专业的改革面板。招聘数据提供岗位需求与市场变化，学生结果仍需对应的学校材料。

## 后续用途

同一数据层可支持岗位技能变化、学历与经验要求、区域产业需求、薪资分布和招聘周期研究。先明确指标、去重口径、时间覆盖和采集来源，再比较不同年份或地区。近期年份数据截断和来源覆盖变化应随汇总一起呈现。

本轮接口、逐项 PASS/FAIL、环境阻断和未验证项统一见 [任务板 W4 验收记录](development-tasks.md#w4--2026-11-10-独立验收记录)。下方保留实际使用方法。

## 本机首次运行

下列 PowerShell 示例使用当前实际目录和明确的 2026 年 CSV 成员。其他机器需替换原包路径和 UnRAR 路径。输出路径使用新目录。

```powershell
$source = 'D:\竞赛数据\比赛数据'
$archive = "$source\应届生招聘数据\分年份保存数据\分年份保存数据.rar"
$unrar = 'D:\WinRAR\UnRAR.exe'
$left = Join-Path $source '“十五五”专项规划69份汇总 (2).zip'
$right = Join-Path $source '“十五五”专项规划69份汇总.zip'

chanjiao warehouse compare-zip --left $left --right $right --output .local/warehouse-run/zip-comparison.json
chanjiao warehouse list-rar --archive $archive --unrar $unrar --output .local/warehouse-run/members.json
chanjiao warehouse unpack --archive $archive --member '分年份保存数据\应届生招聘大数据2026.csv' --unrar $unrar --destination .local/warehouse-run/input/campus-2026.csv --output .local/warehouse-run/extraction.json
chanjiao warehouse ingest --csv .local/warehouse-run/input/campus-2026.csv --database .local/warehouse-run/recruitment.duckdb --dataset-id campus-jobs --version annual-2026 --expected-year 2026 --output .local/warehouse-run/import.json
chanjiao warehouse summary --database .local/warehouse-run/recruitment.duckdb --dataset-id campus-jobs --version annual-2026 --limit 10 --output .local/warehouse-run/summary.json
chanjiao warehouse export --database .local/warehouse-run/recruitment.duckdb --dataset-id campus-jobs --version annual-2026 --destination .local/warehouse-run/campus-2026.parquet --output .local/warehouse-run/export.json
```

同源同版本重跑 ingest 时将报告路径改为 import-retry.json。命令只向终端输出报告路径；summary.json 保存受数量限制的聚合。

## 验收范围与本地产物

已用一个真实年度成员完整执行提取、CRC、入库、幂等重跑、质量汇总和 Parquet 导出。实际行数、日期覆盖、质量计数及来源哈希保存在本机 `.local/warehouse-pilot/`，通用代码与文档单独交付。

复制来的两份规划 ZIP 已逐成员核对，正文内容一致，成员 CRC 通过。文件名明确声明 UTF-8、附加元数据更少的副本可优先使用。文档中的政策事实和具体数字另行核对。

试运行覆盖一个年度。全量质量、跨版本重复及数据来源覆盖仍需按数据集逐项执行相同流程。当前招聘数据可以支持需求侧分析，培养效果仍需学校改革与学生结果材料。
