# 里程碑：Wind 数据源集成完成 (2026-05-21 15:25)

## 完成内容

### 架构改造
- **Pipeline v3**：`sync → enrich → enrich_wind → calc → build → deploy`
- 新增 `step_enrich_wind()`：查询即存储，增量补充，每日限额100只
- `step_build()` 输出新增4字段：custodian、benchmark、management_fee_rate、custody_fee_rate

### 新增/修改文件
| 文件 | 操作 | 用途 |
|------|------|------|
| `pipeline.py` | 修改 | +step_enrich_wind(), 修改step_build(), 注册新步骤 |
| `fetchers/wind_fetcher.py` | 新建 | WindFetcher：查询即存储 + 缓存降级 |
| `fetchers/__init__.py` | 新建 | fetchers 包初始化 |
| `ARCHITECTURE.md` | 新建 | 架构设计文档（数据流/SST原则/目录结构）|
| `overview.md` | 新建 | MVP 现状诊断报告 |

### 关键设计决策
1. **SST原则**：本地 JSON = 单一权威源，外部 API = 临时提供者
2. **Wind 数据独立存储**：`etf_wind_data.json`（与盈米 yingmi 模式一致）
3. **优先级规则**：custodian = Wind > gen，benchmark = Wind > gen
4. **积分控制**：首次 100 只（~667分），全部1470只需 ~10天

---

## 当前数据质量（1470 ETFs）

| 字段 | 覆盖 | 缺口 | 解决方案 |
|------|------|------|----------|
| issuer / issue_date | 100% | - | ✅ Wind 已完成 |
| scale / close / top_holdings | 98%+ | - | ✅ |
| year_1_return | 99.2% | 12只 | 跑 calc |
| max_drawdown / sharpe | 95.8% | 62只 | 跑 calc |
| annual_vol | 94.6% | 79只 | 修复bug+重跑 |
| year_3_return | 79.9% | 295只 | 需756天K线 |
| custodian | 0% | 1470只 | 🔜 Wind fill |
| benchmark | 0% | 1470只 | 🔜 Wind fill |
| mgmt_fee / custody_fee | 0% | 1470只 | 🔜 Wind fill |

---

## 下一步执行清单

### P0（立即）
- [ ] `python pipeline.py enrich_wind` — 首次填充 custodian/benchmark/费率
- [ ] 修复 annual_vol bug（358只未计算）

### P1（本周）
- [ ] 前端 detail.html 展示新字段
- [ ] 分批补充剩余 Wind 数据（10天计划）

### P2（后续）
- [ ] year_3_return 提升到 99%（需K线积累）
- [ ] step_enrich 改为 fetchers 封装