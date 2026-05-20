# ETF工具MVP - 完整版本清单

**统计时间**: 2026-05-20 02:04
**总版本数**: 121 个
**时间范围**: 2026-05-12 至 2026-05-20

---

## 版本清单（按时间编号）

| 编号 | 日期 | 提交哈希 | 版本描述 | 备注 |
|------|------|----------|----------|------|
|   1 | 2026-05-20 | f71af54 | docs: 添加8小时工作计划任务包（数据质量分析+calc_metrics优化） | 文档 |
|   2 | 2026-05-20 | 1bdffe4 | feat: 添加分批吸收脚本（支持--batch和--incremental模式） | 新功能 |
|   3 | 2026-05-20 | 8b7a321 | feat: 添加增量模式支持（只处理缺失year_3_return的ETF） | 新功能 |
|   4 | 2026-05-20 | 574966c | fix: 修复calc_metrics.py多数据源支持（westock-data + 本地缓存 + AKShare） | 修复Bug, 数据相关 |
|   5 | 2026-05-19 | ce3fa28 | feat: 创建financial_data_fetcher/通用数据获取框架（四层架构第1层）\n\n- base_fetcher.py: 基础获取器抽象类（重试/缓存/验证）\n- multi_source_fetcher.py: 多源获取器（ETF实现）\n- cache_manager.py: 缓存管理器（本地/GitHub/PA同步）\n- rate_limiter.py: 限流管理器（指数退避）\n- data_validator.py: 数据验证器（交叉验证/异常检测） | 新功能, 数据相关 |
|   6 | 2026-05-19 | 8d4a4a4 | fix: 三地存储方案 - 修复.gitignore(含data/history) + app.py添加/api/sync端点 + pipeline.py部署后触发PA同步 + 删除data_absorber.py/enrich_missing_fields.py | 修复Bug, 数据相关 |
|   7 | 2026-05-19 | 3262d7f | daily: 2026-05-19数据更新 |  |
|   8 | 2026-05-19 | 2c8d07c | pipeline: 2026-05-19 数据更新 |  |
|   9 | 2026-05-18 | 76332b8 | fix: 修复涨跌幅数据（AKShare列名错误）+ 价格数据重算 | 修复Bug |
|  10 | 2026-05-18 | 22ce028 | fix: 修复prev_close和change_pct数据问题，创建历史缓存文件 | 修复Bug |
|  11 | 2026-05-18 | 126ec9a | feat: daily_update + 历史净值优先本地缓存 | 新功能 |
|  12 | 2026-05-18 | cef564f | feat: 历史净值首选AKShare实时，详情页实时价格覆盖 | 新功能 |
|  13 | 2026-05-18 | 44f379c | feat: add Wind-style professional compare page with report export | 新功能 |
|  14 | 2026-05-18 | 04ced78 | fix: deploy.sh directory path (etf-tool-mvp -> etf-tool-mvp) | 修复Bug, 部署相关 |
|  15 | 2026-05-18 | d329a0f | chore: add one-click deploy script for PythonAnywhere | 部署相关, 杂项 |
|  16 | 2026-05-18 | b40d2cf | fix: P0/P1修复，补充风险指标，改进UX | 修复Bug |
|  17 | 2026-05-18 | 7a06082 | fix: compatible fetch timeout + cleaner bar chart | 修复Bug |
|  18 | 2026-05-18 | c3c5a8f | fix: add fetch timeout to prevent hanging on yingmi API | 修复Bug |
|  19 | 2026-05-18 | 4deb67d | feat: modern single-axis bar chart with normalization | 新功能 |
|  20 | 2026-05-18 | 8478307 | feat: dynamic bar chart with clickable metric chips | 新功能 |
|  21 | 2026-05-18 | 562c59f | fix: button functions missing, typo, volume display, chart sizing | 修复Bug |
|  22 | 2026-05-18 | 3c3fb25 | feat: toggle between self-calc and yingmi on compare page | 新功能 |
|  23 | 2026-05-18 | bbef951 | feat: compare page can fetch yingmi data for all ETFs | 新功能, 数据相关 |
|  24 | 2026-05-18 | 98234b0 | feat: yingmi data 1440/1466 + tie green highlight | 新功能, 数据相关 |
|  25 | 2026-05-18 | 2971238 | feat: 盈米风险指标数据 (1440/1466) | 新功能 |
|  26 | 2026-05-18 | 0b85a09 | fix: highlight wraps text only via span; bar chart uses gold for best bars | 修复Bug |
|  27 | 2026-05-18 | 8f3b3ef | fix: remove holdings row, tighter highlights, gradient bars with best-value gold | 修复Bug |
|  28 | 2026-05-18 | f1f606e | fix: subtle highlights, regroup rows, remove 3yr highlight, core compare only | 修复Bug |
|  29 | 2026-05-17 | 1994f19 | feat: enhanced chart styling - rounded bars, smooth radar, better colors | 新功能 |
|  30 | 2026-05-17 | 45093d5 | fix: bar chart shows scale + volume (same unit) instead of scale + return | 修复Bug |
|  31 | 2026-05-17 | 1a7588b | fix: compare template jinja2 syntax errors | 修复Bug |
|  32 | 2026-05-17 | 807ffb2 | feat: add issue_date to detail and compare pages | 新功能 |
|  33 | 2026-05-17 | c1be025 | feat(D): enhanced compare page with radar chart, bar chart, best-value highlighting | 新功能 |
|  34 | 2026-05-17 | 724315c | feat: risk API reads yingmi JSON first, falls back to CLI | 新功能 |
|  35 | 2026-05-17 | 1bbefa7 | feat: risk page shows self-calc data on load, click button to fetch yingmi | 新功能, 数据相关 |
|  36 | 2026-05-17 | d3cb13c | fix: use dynamic yingmi-skill-cli path for Mac + PythonAnywhere | 修复Bug |
|  37 | 2026-05-17 | 5293e39 | feat: default sort by scale descending on homepage | 新功能 |
|  38 | 2026-05-17 | be2dd1f | feat: risk page click-to-fetch yingmi; AKShare holdings fallback | 新功能 |
|  39 | 2026-05-17 | 754174a | feat: remove max_drawdown/sharpe from detail first layer, keep only in risk page | 新功能 |
|  40 | 2026-05-17 | 93cef23 | feat: separate calc_metrics.py for self-calculated indicators, saved to independent file | 新功能 |
|  41 | 2026-05-17 | 9ad3adb | fix: mobile responsive - table scroll, hide non-essential columns | 修复Bug |
|  42 | 2026-05-17 | 878bdd3 | feat: risk page with on-demand yingmi data, non-convex market_cap for scale | 新功能, 数据相关 |
|  43 | 2026-05-17 | 72d4c26 | feat: add data source footer with cutoff dates and disclaimer | 新功能, 数据相关 |
|  44 | 2026-05-17 | 4f3c505 | fix: year_3_return shows 不足3年 when same as year_1 | 修复Bug |
|  45 | 2026-05-17 | 37d6a01 | fix: scale/percentages to 2 decimal places across all templates | 修复Bug |
|  46 | 2026-05-17 | 1902463 | fix: detail page header shows issuer short name, full name in subtitle | 修复Bug |
|  47 | 2026-05-17 | 89b33bc | fix: add prefix-based issuer matching for non-standard ETF names | 修复Bug |
|  48 | 2026-05-17 | e93267c | feat: list page shows issuer short name, detail page shows full name | 新功能 |
|  49 | 2026-05-17 | ea792a5 | feat: add prev_close and change_rate for all 1466 ETFs | 新功能 |
|  50 | 2026-05-17 | ba15fb4 | feat: issuer now shows full fund company name | 新功能 |
|  51 | 2026-05-17 | cae697e | feat: add shares (基金份额) field, display on detail page | 新功能 |
|  52 | 2026-05-17 | d1514d2 | fix: scale calculation - AKShare returns fund shares, multiply by close for AUM | 修复Bug |
|  53 | 2026-05-17 | f73af3f | fix: change_pct display to 2 decimal places | 修复Bug |
|  54 | 2026-05-17 | 535cb2e | fix: default sort by code asc instead of scale desc | 修复Bug |
|  55 | 2026-05-17 | 24c95fc | fix: always convert market_cap/volume to 亿 (remove incorrect threshold) | 修复Bug |
|  56 | 2026-05-17 | c33155c | fix: wrap loadETFs in try-catch, use DOMContentLoaded, handle null elements | 修复Bug |
|  57 | 2026-05-17 | ce4d17a | cleanup: delete 88 abandoned files (old scripts, temp data, docs, backups) | 数据相关, 文档 |
|  58 | 2026-05-17 | 805a7e5 | fix: JS crash from undefined etf.type in badge class logic | 修复Bug |
|  59 | 2026-05-17 | 0faac36 | fix: prominent price display on detail page, fix null type in list | 修复Bug |
|  60 | 2026-05-17 | 0829775 | fix: add price column to ETF list table | 修复Bug |
|  61 | 2026-05-17 | 77e4c7e | fix: use AKShare 2026 Q1 portfolio data for accurate holdings (replace non-convex component list) | 修复Bug, 数据相关 |
|  62 | 2026-05-17 | f2f6e81 | fix: remove fee/tracking_error/launch_date references from API and screening | 修复Bug |
|  63 | 2026-05-17 | 3193a90 | fix: update templates for removed fee/launch/underlying fields, replace with change_pct | 修复Bug |
|  64 | 2026-05-17 | 57d7d94 | refactor: remove fee/launch_date/underlying fields (no reliable data source) | 数据相关, 重构 |
|  65 | 2026-05-17 | b74f63b | fix: remove unreliable old enrich data, scale/launch_date/fee now from AKShare raw | 修复Bug, 数据相关 |
|  66 | 2026-05-17 | 591ada4 | feat: add close price and change_pct fields to all 1466 ETFs | 新功能 |
|  67 | 2026-05-17 | 1e1f1b6 | feat: add change_pct field from AKShare snapshot, add enrich_prices.py for close prices | 新功能 |
|  68 | 2026-05-17 | a7abfc0 | chore: remove GitHub Actions deploy (free PA account API limitations) | 部署相关, 杂项 |
|  69 | 2026-05-17 | 422af52 | refactor: deploy.py only does Reload (git pull handled by PA scheduled task) | 部署相关, 重构 |
|  70 | 2026-05-17 | aed23f1 | fix: use Schedule API for git pull instead of Console (console needs browser) | 修复Bug |
|  71 | 2026-05-17 | b26f438 | fix: correct PA API version - consoles use /api/v0/, reload uses v0 webapps | 修复Bug |
|  72 | 2026-05-17 | 2ed570c | debug: print HTTP status and response body for console API |  |
|  73 | 2026-05-17 | 88246f8 | fix: add fallback to reload-only if console creation fails + debug output | 修复Bug |
|  74 | 2026-05-17 | 9f551e5 | fix: use Python script for PA API calls with proper error handling | 修复Bug |
|  75 | 2026-05-17 | 92ec4a2 | fix: use JSON body for PA API console/create and send_input | 修复Bug |
|  76 | 2026-05-17 | 9a685ad | fix: remove actions/checkout (not needed for PA API deploy), clean Node 20 warning | 修复Bug, 部署相关 |
|  77 | 2026-05-17 | 03223c0 | chore: add FORCE_JAVASCRIPT_ACTIONS_TO_NODE24 to fix Node 20 deprecation warning | 修复Bug, 杂项 |
|  78 | 2026-05-17 | 2aa5611 | test: trigger deploy to verify GitHub Actions | 部署相关, 测试 |
|  79 | 2026-05-17 | 5eb1d53 | fix: rewrite GitHub Actions deploy with proper auth and reload API | 修复Bug, 部署相关 |
|  80 | 2026-05-17 | 2ec8d22 | feat: full data enrichment - 1433 real returns, 1402 drawdown/sharpe, 1274 holdings | 新功能, 数据相关 |
|  81 | 2026-05-17 | 81d0b30 | chore: remove SSH keys from repo, update .gitignore, fix etf_data.py sys import | 修复Bug, 数据相关, 杂项 |
|  82 | 2026-05-17 | df19b21 | perf: 列表页分页渲染(P50行) + 表头排序 + 按需字段(P10个) |  |
|  83 | 2026-05-17 | 111cd43 | update data | 数据相关 |
|  84 | 2026-05-17 | adb97d6 | feat: 方案B全量数据补充脚本 | 新功能 |
|  85 | 2026-05-17 | e4928ba | refactor: 拆分为独立可复用模块 | 重构 |
|  86 | 2026-05-17 | 3d80483 | feat: 新增 enrich_all_etfs.py 覆盖全部1466只ETF的持仓权重和净值计算 | 新功能 |
|  87 | 2026-05-17 | 91a593b | fix: 修复AKShare规模数据获取（列索引定位）及重新标准化 | 修复Bug |
|  88 | 2026-05-17 | facacf9 | feat: 补齐免费数据源的持仓权重和历史净值计算 | 新功能 |
|  89 | 2026-05-16 | 302b254 | feat: 从东方财富(AKShare)源头重建ETF数据库，彻底解决数据质量问题 | 新功能 |
|  90 | 2026-05-16 | 55bc154 | refactor: 重建 ETF 数据加载架构 | 重构 |
|  91 | 2026-05-16 | eebf71e | chore: 清理 _extract_name_issuer 中残留的死代码 | 杂项 |
|  92 | 2026-05-16 | 3530dce | feat: 从全量数据 name 自动提取发行人，覆盖 1169/1461 只 ETF | 新功能 |
|  93 | 2026-05-16 | 54dd4db | fix: issuer为空时不显示尾部 '-'，避免显示冗余后缀 | 修复Bug |
|  94 | 2026-05-16 | 9720d87 | fix: 持仓列表名称加 flex:1 对齐优化 | 修复Bug |
|  95 | 2026-05-16 | 4171ff8 | fix: 修复 top_holdings 前端渲染，统一为字典格式 | 修复Bug |
|  96 | 2026-05-16 | bae8e66 | fix: 修复 top_holdings 数据串用问题，重新获取真实持仓 | 修复Bug |
|  97 | 2026-05-16 | 5a35d28 | fix: 改为全量1461只底座 + 优质数据补充，解决只显示130只的问题 | 修复Bug |
|  98 | 2026-05-16 | 174d15d | fix: 名称显示格式改为 代码-名称-基金公司 | 修复Bug |
|  99 | 2026-05-16 | 1f155dd | fix: 修复收益率/夏普/最大回撤数值错误（去掉多余的/100转换） | 修复Bug |
| 100 | 2026-05-16 | b9b483f | fix: etf_data.py 支持 etf_data_generated.json，修复 top_holdings 不显示 | 修复Bug, 数据相关 |
| 101 | 2026-05-16 | f536df6 | fix: 升级 actions/checkout@v4 + setup-python@v5，修复 Node.js 20 废弃警告；修复 YAML 缩进及 Python 语法错误 | 修复Bug |
| 102 | 2026-05-16 | 9e66f0d | fix: etf_data.py 修复 UnboundLocalError + 延长数据有效期至7天 | 修复Bug, 数据相关 |
| 103 | 2026-05-16 | dc65b47 | chore: 更新 etf_complete_130.json 数据 | 杂项 |
| 104 | 2026-05-15 | a6dcf63 | fix: etf_data.py 修复字段映射（symbol_id→code）及关键词搜索 | 修复Bug, 数据相关 |
| 105 | 2026-05-14 | d7989d0 | refactor: 改用 PythonAnywhere API 部署（免 SSH，免费账户可用） | 重构 |
| 106 | 2026-05-14 | 06550bc | fix: 修复 deploy.yml bash 语法错误 [[]] | 修复Bug, 部署相关 |
| 107 | 2026-05-14 | 214eeb8 | 修复 GitHub Actions：测试失败不影响部署 |  |
| 108 | 2026-05-14 | de18903 | 配置 GitHub Actions 自动部署到 PythonAnywhere |  |
| 109 | 2026-05-14 | a63b055 | 更新 ETF 数据：使用重建的 1461 只 ETF 全量数据 |  |
| 110 | 2026-05-14 | 40c7bbe | Fix duplicate manager name in ETF display | 修复Bug |
| 111 | 2026-05-14 | 15f2fd8 | Add deployment script and API test | 部署相关, 测试 |
| 112 | 2026-05-14 | 06c13ed | Initial deployment | 部署相关 |
| 113 | 2026-05-13 | 855dd75 | 修改ETF名称格式为：代码-名称-基金公司，避免同名混淆 |  |
| 114 | 2026-05-13 | c5b89e4 | 修复ETF持仓数据：更新159915/512650/159901/515800的top_holdings为东方财富网真实数据 |  |
| 115 | 2026-05-13 | 38698f7 | 修复8只ETF的持仓数据 (510300,510500,510050,159915,512100,159967,510880,512800) |  |
| 116 | 2026-05-12 | 5699679 | 添加真实的前五大持仓股票数据 |  |
| 117 | 2026-05-12 | 8ebb483 | 添加专业README.md - 完善项目文档 |  |
| 118 | 2026-05-12 | c1de87a | 添加ETF筛选器创业方案V2.md |  |
| 119 | 2026-05-12 | 266b795 | Add Render deployment guide | 部署相关 |
| 120 | 2026-05-12 | a84112d | Make app cloud-ready: use dynamic PORT for Render deployment | 部署相关 |
| 121 | 2026-05-12 | bd08855 | Initial commit: ETF筛选器MVP - 包含130只ETF数据和筛选功能 |  |

---

## 版本演进分析

### 阶段1: MVP初始版本

**提交数**: 1 个

- `bd08855` 2026-05-12 - Initial commit: ETF筛选器MVP - 包含130只ETF数据和筛选功能

---

## 重要版本标记

### 稳定版本（推荐回退）
- **版本97** (`4f3c505`): 数据质量相对稳定
- **版本113** (`latest`): 当前最新版本

### 问题版本（谨慎使用）
- **版本65** (`ce4d17a`): 删除了88个文件，可能导致功能缺失

---

## 缓存文件删除记录

以下缓存文件在版本65被删除（可从git历史恢复）：
- `etf_data_130.json`
- `etf_data_1461.json`
- `etf_risk_indicators.json`
- `etf_top_holdings.json`
- `etf_data_with_returns.json`
- ... 等共28个文件

**恢复命令**：
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
git checkout ce4d17a~1 -- data_generated/
```

---

## 当前文件清单

### 核心文件（22个）
- `app.py` - Flask主应用
- `etf_data.py` - 数据加载模块
- `data_fetcher.py` - 数据获取
- `data_processor.py` - 数据处理
- `calc_metrics.py` - 指标计算
- `enrich_prices.py` - 价格补充
- `enrich_holdings.py` - 持仓补充
- `templates/index.html` - 列表页
- `templates/detail.html` - 详情页
- `templates/risk.html` - 风险页
- `data_generated/etf_data.json` - 核心数据(1463只)
- `data_generated/etf_prices.json` - 价格数据
- `data_generated/etf_holdings.json` - 持仓数据

### 文档文件
- `README.md`
- `deploy.py`
- `deploy.sh`
- `ETF_工具MVP_完整版本清单.md`
- `ETF_data_indicators_analysis.md`
- `distributed_cache_architecture.md`

---

## 使用建议

1. **保留所有版本**：git历史完整，随时可回退
2. **恢复被删文件**：从版本64恢复缓存文件
3. **版本对比**：使用 `git diff` 对比不同版本
4. **稳定版本**：版本97或版本113

---

**自动生成时间**: {now}
**脚本路径**: `version_tracker.py`
**运行命令**: `python3 version_tracker.py`
