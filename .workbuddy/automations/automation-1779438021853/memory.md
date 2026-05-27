# ETF 每日数据更新 - 执行历史

## 2026-05-27

### 执行摘要
- **状态**: 成功
- **时间**: 03:02 - 03:30

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | AKShare sync → enrich → calc → build → deploy 完成 |
| 2. wequote_daily.py | 成功 | WeStock 补充行情完成（需 `-u` 无缓冲模式） |
| 3. git commit + push | 成功 | 提交 wequote 补充数据 |
| 4. PA 同步 curl | 失败(401) | 未授权，需检查 API token |

### 数据更新
- Pipeline: 1480 只 ETF（+3），git push 成功，242 个版本
- WeStock: quote 更新 1480 个字段，etf 更新 1184 个字段，总计 2664 字段
- Git: 2673 行新增，2229 行删除

### 踩坑记录
- wequote_daily.py 首次运行因 Python stdout 缓冲被判定超时 kill，改用 `python3 -u` 无缓冲模式解决
- 脚本实际运行约 15 分钟（148 批次 quote + 148 批次 etf，每批 10 个，含 1.5s 间隔）

### 问题
- PA 同步返回 401 Unauthorized（连续 3 天），需检查 PythonAnywhere API 认证

---

## 2026-05-26

### 执行摘要
- **状态**: 成功
- **时间**: 03:01 - 03:24

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | AKShare sync → enrich → calc → build → deploy 完成 |
| 2. wequote_daily.py | 成功 | WeStock 补充行情完成 |
| 3. git commit + push | 成功 | 提交 wequote 补充数据 |
| 4. PA 同步 curl | 失败(401) | 未授权，需检查 API token |

### 数据更新
- Pipeline: 1477 只 ETF，git push 成功
- WeStock: quote 更新 1477 个字段，etf 更新 1184 个字段
- Git: 2652 行新增，2208 行删除

### 问题
- PA 同步返回 401 Unauthorized，需检查 PythonAnywhere API 认证

---

## 2026-05-25

### 执行摘要
- **状态**: 成功（含修复）
- **时间**: 03:00 - 03:27

### 各步骤状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. pipeline.py --push --no-wind | 成功 | AKShare sync → enrich → calc → build → deploy 完成 |
| 2. wequote_daily.py | 成功 | WeStock 补充行情完成 |
| 3. git commit + push | 成功 | 提交 wequote 补充数据 |
| 4. PA 同步 curl | 失败(401) | 未授权，需检查 API token |

### 数据更新
- Pipeline: 1475 只 ETF，git push 成功
- WeStock: quote 更新 1475 个字段，etf 更新 592 个字段
- Git: 2066 行新增，1844 行删除

### 修复记录
- 修复 `modules/local_store.py` 中 `create_snapshot` 对 dict 格式数据的兼容问题
- 原代码假设 `etf_standard_data.json` 是列表，实际为 `{"etfs": [...], "updated": "..."}`

### 问题
- PA 同步返回 401 Unauthorized，需检查 PythonAnywhere API 认证
