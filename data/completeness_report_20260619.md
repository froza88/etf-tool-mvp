# ETF Data Completeness — Production Report
# ETF 数据完整度 — 投产报告

**Date / 日期: 2026-06-19** | **Valid Equity ETFs / 有效权益ETF: 1140**
**Total / 全量: 1549** (债券/60 band 短期/349 short excluded 已排除)
**Wind Cache / Wind缓存: 1549/1549 (100%)**

| # | 中文 | English | Valid | % | Status |
|---|------|---------|-------|----|--------|
| 代码 | Code | 1140/1140 | 100% | ✅ |
| 名称 | Name | 1140/1140 | 100% | ✅ |
| 规模(亿) | AUM | 1140/1140 | 100% | ✅ |
| 收盘价 | Close | 1140/1140 | 100% | ✅ |
| 涨跌幅% | Chg% | 1139/1140 | 100% | ✅ |
| 成交量 | Volume | 1140/1140 | 100% | ✅ |
| 近1年收益% | 1Y Return | 1140/1140 | 100% | ✅ |
| 最大回撤% | Max DD | 1140/1140 | 100% | ✅ |
| 夏普比率 | Sharpe | 1140/1140 | 100% | ✅ |
| 年化波动% | Ann Vol | 1140/1140 | 100% | ✅ |
| 卡玛比率 | Calmar | 1140/1140 | 100% | ✅ |
| 跟踪误差% | Track Err | 1136/1140 | 100% | ✅ |
| 跟踪指数 | Benchmark | 1140/1140 | 100% | ✅ |
| 管理费率% | Mgmt Fee | 1125/1140 | 99% | ✅ |
| 托管费率% | Custody Fee | 1125/1140 | 99% | ✅ |
| 总费率% | Total Fee | 1125/1140 | 99% | ✅ |
| 投资类型 | Inv Type | 1133/1140 | 99% | ✅ |
| 托管人 | Custodian | 1140/1140 | 100% | ✅ |
| 基金经理 | Manager | 1124/1140 | 99% | ✅ |
| 信息比率 | Info Ratio | 1140/1140 | 100% | ✅ |
| 贝塔 | Beta | 1136/1140 | 100% | ✅ |
| 阿尔法 | Alpha | 1136/1140 | 100% | ✅ |
| 估值分位% | Val %ile | 871/1140 | 76% | ❌ |

## Production Assessment / 投产评估
- ✅ ≥98% Ready /**就绪**: 22 fields
- ⚠️ 90-98% Near /**接近**: 0 fields
- ❌ Gaps /**缺口**: 1 fields

## Gap Detail / 缺口明细
| Field / 字段 | Status | Root Cause / 根因 | Plan / 计划 |
|--------------|--------|-------------------|-------------|
| 估值分位 (Val %ile) | 871/1140 (76%) | iFind rate-limited / 日限额已满 | Resume 6/20 / 明天续跑 |
| 资金流入 (5D Flow) | 0/1140 (0%) | Proxy blocks Eastmoney / 代理拦截东方财富 | Need proxy bypass / 需绕过代理 |

## Data Source Summary / 数据源汇总
| Source / 源 | Purpose / 用途 | Status |
|-------------|---------------|--------|
| Wind MCP (Key 1+2) | Fund-level: fees, risk, NAV / 费率/风险/净值 | ✅ 1549 caches |
| iFind MCP | Index PE percentile / 指数估值分位 | ⚠️ Rate-limited, resume 6/20 |
| Tencent Quotes / 腾讯行情 | Real-time close prices / 实时收盘价 | ✅ 83 ETFs filled |
| AKShare | Index valuation (backup) / 指数估值(备用) | ❌ Proxy blocked |
| Eastmoney / 东方财富 | Fund flow / 资金流入 | ❌ Proxy blocked |
| Non凸 (FTShare) | ETF detail/holdings / ETF详情/持仓 | ⏳ Available, not deeply used |

## Wind Query Optimization / Wind查询优化
**Optimal combined format / 最优合并提问:** 
"管理费率 托管费率 风险指标 贝塔 阿尔法 信息比率" → 7 fields in 1 call
Previously: 3 separate calls (费率 + 风险 + 标准) → now 2 calls (标准 + 合并)
Efficiency gain / 效率提升: 33% fewer Wind API calls