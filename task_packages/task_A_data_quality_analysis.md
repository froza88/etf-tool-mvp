# 任务包A：ETF数据质量分析报告

## 背景

你是一个ETF数据分析专家。我需要你分析当前ETF数据集的数据质量，找出为什么部分ETF缺少 `year_3_return`（3年回报率）数据。

## 项目信息

- **项目路径**：`/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/`
- **数据文件**：`etf_standard_data.json`（1467只ETF）
- **目标字段**：`year_3_return`（3年回报率）
- **当前覆盖率**：约85%（假设批量吸收任务已完成）

## 你的任务

### 1. 读取数据文件
```python
import json
with open('/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/etf_standard_data.json', 'r') as f:
    data = json.load(f)
```

### 2. 统计各字段覆盖率
分析以下字段的覆盖率（有值的ETF数量/总数）：
- `year_3_return`（3年回报率）
- `year_1_return`（1年回报率）
- `sharpe_ratio`（夏普比率）
- `max_drawdown`（最大回撤）
- `holdings`（持仓明细）
- `issuer`（管理人）
- `scale`（规模）

输出表格，例如：
| 字段 | 有值数量 | 覆盖率 |
|------|---------|--------|
| year_3_return | 1247 | 85.0% |
| ... | ... | ... |

### 3. 分析缺失 `year_3_return` 的ETF特征
找出所有 `year_3_return` 为0或缺失的ETF，分析它们的共同特征：
- **上市日期分布**：是不是都是2023年之后上市的（历史<3年）？
- **ETF类型**：是不是都是货币/债券/商品ETF（不需要3年回报率）？
- **交易所分布**：沪市/深市/北交所？
- **规模分布**：是不是都是小规模ETF（<1亿）？

输出分析报告，包含：
- 缺失ETF数量
- 按上市日期分组的统计
- 按ETF类型分组的统计
- 结论：为什么这些ETF没有 `year_3_return` 数据？

### 4. 生成报告
将分析结果保存为Markdown文件：
**文件路径**：`/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/data_quality_report.md`

报告结构：
```markdown
# ETF数据质量分析报告
生成时间：YYYY-MM-DD HH:MM

## 1. 数据概览
- 总ETF数量：1467
- 数据更新时间：...

## 2. 字段覆盖率
（表格）

## 3. 缺失 year_3_return 的ETF分析
（分析结果）

## 4. 结论与建议
（是否可以补充数据？如何补充？）
```

## 交付物

1. **数据质量报告**：`/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/data_quality_report.md`
2. **控制台输出**：关键统计数据的打印输出

## 注意事项

- 如果 `etf_standard_data.json` 文件不存在，请先检查项目目录
- 如果 `year_3_return` 覆盖率已经是100%，说明所有ETF都有数据，任务完成
- 分析报告要简洁清晰，用表格和图表（文字描述）呈现

## 项目上下文（供参考）

这是"ETF工具MVP"项目，目标是构建一个ETF数据分析工具。当前阶段是提升数据质量，特别是 `year_3_return` 字段的覆盖率。

数据源：
- 非凸科技 API（market.ft.tech）：提供ETF详情、收益率等
- AKShare：备用数据源
- 盈米：风险指标数据

已完成的脚本：
- `absorb_batch.py`：分批从非凸API吸收数据
- `calc_metrics.py`：计算ETF指标（收益率、夏普比率等）

---

**开始执行任务吧！**
