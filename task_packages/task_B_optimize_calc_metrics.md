# 任务包B：优化 calc_metrics.py 补充缺失数据

## 背景

你是一个Python工程师和数据分析专家。我需要你优化 `calc_metrics.py` 脚本，使其能够补充缺失的 `year_3_return`（3年回报率）数据。

## 项目信息

- **项目路径**：`/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/`
- **目标脚本**：`calc_metrics.py`
- **数据文件**：`etf_standard_data.json`（1467只ETF）
- **问题**：部分ETF缺少 `year_3_return` 数据（覆盖率约85%）

## 你的任务

### 1. 读取并理解 `calc_metrics.py`

先读取脚本，理解其当前逻辑：
```bash
cat /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/calc_metrics.py
```

关注点：
- 如何获取历史价格数据？
- 如何计算 `year_3_return`？
- 失败/缺失时如何处理？

### 2. 优化数据获取逻辑

当前脚本可能只使用单一数据源（非凸API）。优化方案：

**多数据源降级策略**：
1. **本地缓存**（`data/history/{code}.json`）：优先使用已下载的历史数据
2. **westock-data kline**（`node scripts/index.js kline`）：从非凸获取K线
3. **AKShare**（`ak.fund_etf_hist_em`）：从AKShare获取历史价格
4. **盈米API**：如果以上都失败，尝试盈米

修改 `get_prices_multi_source()` 函数，实现4级降级。

### 3. 优化计算逻辑

对于缺失 `year_3_return` 的ETF：
- 如果有≥756天价格数据（3年×252交易日），计算 `year_3_return`
- 如果数据不足3年，设置 `year_3_return = 0` 或 `null`
- 记录日志：哪些ETF无法计算（原因：数据不足/API失败）

### 4. 添加健壮的错误处理

当前脚本可能在单个ETF失败时崩溃。优化：
- 用 `try-except` 包裹每个ETF的处理逻辑
- 失败时任然继续处理下一个ETF
- 保存失败列表到日志文件

### 5. 测试优化后的脚本

在一小部分ETF上测试（例如前10只）：
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
python3 -c "
from calc_metrics import calc_all_metrics
result = calc_all_metrics(limit=10)
print(result)
"
```

### 6. 保存优化后的脚本

将优化后的脚本保存回原位置：
**文件路径**：`/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/calc_metrics.py`

## 交付物

1. **优化后的 `calc_metrics.py`**：覆盖原文件
2. **测试报告**：控制台输出或日志文件
3. **优化说明**：简要说明做了哪些改进

## 代码规范

- 使用中文注释（项目惯例）
- 保持代码简洁可读
- 添加必要的日志记录
- 不要删除原有功能，只做优化

## 项目上下文（供参考）

### 数据结构

`etf_standard_data.json` 是ETF标准数据集，结构：
```json
[
  {
    "code": "510300",
    "name": "沪深300ETF",
    "year_3_return": 12.5,
    ...
  },
  ...
]
```

### 依赖环境

- Python 3.9+
- 依赖库：akshare, requests, json
- 可能需要安装：`pip install akshare`

### 相关脚本

- `absorb_batch.py`：从非凸API吸收数据（已优化）
- `data_absorber.py`：数据吸收器（旧版）
- `pipeline.py`：数据流水线（sync → enrich → calc → build）

## 开始执行

请先读取 `calc_metrics.py`，理解当前逻辑，然后开始优化。

如果遇到问题（如缺少依赖、文件路径错误），请在输出中说明，我会协助解决。

---

**开始执行任务吧！**
