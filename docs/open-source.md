# 开源参考

2026-11-09 核对。提交用于记录阅读快照，运行版本以 pyproject 和环境文件为准。

statsmodels 为 BSD-3-Clause，实际依赖 0.15.0，调用 OLS.fit(cov_type="HC3", use_t=True)。领域校验和工作流由本项目编写。[快照与源码](https://github.com/statsmodels/statsmodels/tree/772cb34aff9e95f5c3eb10f1fe1ff6cd393daa69) · [许可证](https://github.com/statsmodels/statsmodels/blob/772cb34aff9e95f5c3eb10f1fe1ff6cd393daa69/LICENSE.txt)

Cookiecutter Data Science 为 MIT，借鉴原始数据、源码、文档和产物分离。仓库手工建立最小布局。[快照](https://github.com/drivendataorg/cookiecutter-data-science/tree/17c991b0b03668f6e36503a4416202900196f501) · [许可证](https://github.com/drivendataorg/cookiecutter-data-science/blob/17c991b0b03668f6e36503a4416202900196f501/LICENSE)

DoWhy 为 MIT，借鉴建模、识别、估计、反驳流程。首版没有接入其运行时，伪改革和删除单位诊断在固定简单设计下自行组织。[快照](https://github.com/py-why/dowhy/tree/b276d75cf7504b8fac246c2f4b54aa7d387cc7d0) · [许可证](https://github.com/py-why/dowhy/blob/b276d75cf7504b8fac246c2f4b54aa7d387cc7d0/LICENSE)

后续候选包括 BSD-3-Clause 的 DoubleML 和 MIT 的 pyBKT，当前没有安装或验证两者。选定版本时须重新核对 API 和授权。[DoubleML](https://github.com/DoubleML/doubleml-for-py) · [pyBKT 快照](https://github.com/CAHLR/pyBKT/tree/0f4ea412e18f6bcbd396fdf2be68fdd43aebebb6)

通过依赖复用的实现保留在上游包中。直接复制或改写文件时保留版权与许可，在此登记本地路径、固定提交和修改范围。外部数据独立登记许可和再分发范围。
