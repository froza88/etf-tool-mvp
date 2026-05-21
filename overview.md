# MVP 现状诊断 + Wind 集成完成

## 一、MVP 可用性评估

### Flask 应用：✅ 可用
- app.py 0 外部 API 调用（符合 PythonAnywhere 限制）
- 4 层历史数据降级：本地文件 → 缓存 → AKShare(开发) → 模拟
- 完整 API：列表筛选、详情、对比、风险指标

### 数据覆盖（1470 只 ETF）

| 字段 | 覆盖 | 评级 |
|------|------|------|
| issuer | 100.0% | ✅ |
| issue_date | 100.0% | ✅ |
| scale / close | 99.7%+ | ✅ |
| top_holdings | 98.9% | ✅ |
| year_1_return | 99.2% | ✅ |
| max_drawdown | 95.8% | ⚠️ |
| sharpe_ratio | 95.8% | ⚠️ |
| annual_vol | 94.6% | ⚠️ |
| year_3_return | 79.9% | ❌ 需更多K线 |
| **custodian** | **0%** | ❌ 新字段，Wind 可补 |
| **benchmark** | **0%** | ❌ 新字段，Wind 可补 |
| **management_fee_rate** | **0%** | ❌ 新字段，Wind 可补 |

## 二、本次改动

修改 `pipeline.py`，新增 `enrich_wind` 步骤：

```
Pipeline v3: sync → enrich → enrich_wind → calc → build → deploy
                                     ↑ 新增
```

### 关键设计
1. **查询即存储**：每次 Wind API 调用自动缓存到 `data/cache/wind/{code}.json`
2. **增量补充**：只查询缺失字段的 ETF，已有数据跳过
3. **每日限额**：每次最多 100 只（约 667 积分），不耗尽配额
4. **降级策略**：Wind API 失败时，使用过期缓存兜底

### 修改文件
- `pipeline.py`：+80 行 step_enrich_wind()，修改 step_build() 合并 Wind 字段
- `ARCHITECTURE.md`：更新完成状态和优先级

### 新增字段（etf_standard_data.json）
- `custodian`：基金托管人（Wind 补充）
- `benchmark`：业绩比较基准（Wind 补充）
- `management_fee_rate`：管理费率（Wind 补充）
- `custody_fee_rate`：托管费率（Wind 补充）

## 三、下一步建议

| 优先级 | 任务 | 详情 |
|--------|------|------|
| P0 | 运行 `python pipeline.py enrich_wind` | 填充 custodian/benchmark/费率，首次约需 100 次调用 |
| P0 | 修复 annual_vol bug | 358 只 ETF 的 annual_vol 未计算 |
| P0 | 补充 year_3_return K线 | 需 756 天 K 线，当前 79.9% |
| P1 | 前端展示新字段 | detail.html 增加 benchmark/费率显示 |
| P1 | 继续 Wind 分批填充 | 剩余 ~1370 只需约 10 天 |