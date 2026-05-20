# calc_metrics.py 代码优化报告

> 优化日期：2026-05-20    
> 文件路径：etf-tool-mvp/calc_metrics.py    

---

## 优化概述

对 ETF 风控指标计算脚本进行了全面的错误处理增强和健壮性优化，版本从 v1 升级到 v2。

---

## 改动清单

### 1. 错误处理增强

| 问题 | 修复前 | 修复后 |
|------|--------|--------|
| 裸 `except:` 吞掉所有异常 | 4 处 `except:` 或 `except: pass` | 全部改为 `except Exception as e:` + 日志记录 |
| AKShare 调用无超时保护 | 直接调用 `ak.fund_etf_hist_em()` | 线程 + 45秒超时，超时自动跳过 |
| subprocess 无错误上下文 | 只捕获异常不记录原因 | 区分 TimeoutExpired / FileNotFoundError / 其他错误 |
| calc_max_drawdown 无防护 | 空列表或 peak=0 可导致除零 | 添加 len<2 和 peak==0 检查 |

### 2. 日志系统

新增完整的 logging 配置：
- 同时输出到文件（`calc_metrics.log`）和终端
- 每个 ETF 的处理过程可追溯
- 区分 debug / info / warning / error 四个级别

### 3. 断点续跑

新增 checkpoint 机制：
- 每 50 只 ETF 自动保存进度
- 脚本中断后重新启动可自动续跑
- checkpoint 文件：`etf_calculated_metrics_checkpoint.json`

### 4. 数据质量改进

| 改动 | 原因 |
|------|------|
| 无数据返回 `None` 而非 `0` | 避免"真正 0 收益"与"无数据"混淆 |
| 夏普比率异常值过滤 | 夏普 >20 或 <-20 标记为无效，防止异常值污染 |
| 日均收益率用无偏方差 | 从总体方差改为样本方差（n-1） |

### 5. 计算函数重构

- 新增 `safe_div()`：安全除法，分母为0返回 default
- `calc_max_drawdown`：返回 None 表示数据不足（而非 0）
- `calc_sharpe`：返回 None 而非 0，加异常值过滤
- `calc_annual_vol`：返回 None 而非 0

### 6. 数据源容错

| 改动 | 说明 |
|------|------|
| westock-data 路径动态查找 | 不再硬编码，多路径候选 |
| ETF 列表文件容错 | 优先 `etf_standard_data.json`，兜底 `etf_complete_all.json` |
| 每个数据源独立异常捕获 | 一个源失败不影响其他源 |

### 7. 主流程改进

- 每只 ETF 独立 try-except，单只失败不影响其他
- 每 50 只输出进度日志（含处理速度）
- 最终输出含总数 / 成功数 / 失败数 / 跳过数 / 耗时

---

## 文件变更

| 文件 | 操作 | 行数 |
|------|------|------|
| `calc_metrics.py` | 重写 | ~280行 → ~350行 |

---

## 使用方式

```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
python3 calc_metrics.py
```

支持中断后续跑，无需额外参数。

---

*优化工程师：寇豆码 · 2026-05-20*