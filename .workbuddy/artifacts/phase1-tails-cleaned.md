# Phase 1 收尾 — 3 个尾巴清理完成

## 完成内容

### 1. NeoDataRepo v1.1 — 实时数据解析 🎯
**之前**：price=0.0 占位，所有字段靠 pipeline 跑  
**现在**：从 NeoData API 的 Markdown 表格中实时提取：

| 来源 | 提取字段 |
|------|----------|
| apiRecall[0] 实时行情 | price, pre_close, open, high, low, volume, nav |
| apiRecall[1] 份额规模 | scale(自动/亿), share_count |
| apiRecall[2] 净值收益率 | year_1_return, year_3_return, change_pct, 多个区间回报率 |
| apiRecall[3] 资产配置 | holdings_overview(股票/银行存款/其他占比) |

**实测 510300**：price=4.871 ✅ scale=1542.18亿 ✅ y1=28.43% ✅ y3=32.37% ✅

### 2. CompositeRepo 缓存写入 📁
**之前**：`_write_to_cache` 是 TODO 空实现，只打日志  
**现在**：写入 `data/neodata_cache/{code}.json`，pipeline 可消费

### 3. Bugfix 三连 🔧
- `allbacks` → `fallbacks`（两处拼写错误）
- `app.py` 构造参数补上 list 包裹：`CompositeRepo(local, [online])`
- NeoData entity name 字段映射修正

## 文件变更
- `repositories/neodata_repo.py` — +200 行（Markdown 解析逻辑）
- `repositories/composite_repo.py` — 修复 typo + 实现缓存写入
- `app.py` — 1 行修改 `[online]`