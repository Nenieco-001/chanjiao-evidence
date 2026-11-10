# 开源参考

这份文档记录首版依据的开源项目、核对日期、许可证和借用范围。2026-11-09 核对；实际运行版本以 `pyproject.toml` 和环境文件为准。

| 项目 | 许可证 | 本项目怎么用 | 链接 |
| --- | --- | --- | --- |
| statsmodels 0.15.0 | BSD-3-Clause | 实际统计依赖，调用 `OLS.fit(cov_type="HC3", use_t=True)`；领域校验和工作流由本项目编写。 | [快照与源码](https://github.com/statsmodels/statsmodels/tree/772cb34aff9e95f5c3eb10f1fe1ff6cd393daa69) · [许可证](https://github.com/statsmodels/statsmodels/blob/772cb34aff9e95f5c3eb10f1fe1ff6cd393daa69/LICENSE.txt) |
| DuckDB 2.0.0 | MIT | 2026-11-10 加入的本地招聘数据仓库，负责有内存限制的 CSV 扫描、SQL 类型化、版本与质量汇总、Parquet 导出。 | [Python 接口](https://duckdb.org/docs/2.0/clients/python/overview) · [固定版本许可证](https://github.com/duckdb/duckdb-python/blob/v2.0.0/LICENSE) |
| Cookiecutter Data Science | MIT | 借鉴原始数据、源码、文档、产物分离的目录思路；仓库手工建立最小布局。 | [快照](https://github.com/drivendataorg/cookiecutter-data-science/tree/17c991b0b03668f6e36503a4416202900196f501) · [许可证](https://github.com/drivendataorg/cookiecutter-data-science/blob/17c991b0b03668f6e36503a4416202900196f501/LICENSE) |
| DoWhy | MIT | 借鉴建模、识别、估计、反驳的流程；没有接入运行时，伪改革和删除单位诊断由本项目按固定简单设计自行组织。 | [快照](https://github.com/py-why/dowhy/tree/b276d75cf7504b8fac246c2f4b54aa7d387cc7d0) · [许可证](https://github.com/py-why/dowhy/blob/b276d75cf7504b8fac246c2f4b54aa7d387cc7d0/LICENSE) |

后续候选：BSD-3-Clause 的 [DoubleML](https://github.com/DoubleML/doubleml-for-py) 和 MIT 的 [pyBKT 快照](https://github.com/CAHLR/pyBKT/tree/0f4ea412e18f6bcbd396fdf2be68fdd43aebebb6)。两者当前都没有安装或验证，选定版本时须重新核对 API 和授权。

通过依赖复用的实现保留在上游包中。直接复制或改写文件时，保留版权与许可，并在这里登记本地路径、固定提交和修改范围。外部数据单独登记许可和再分发范围。
