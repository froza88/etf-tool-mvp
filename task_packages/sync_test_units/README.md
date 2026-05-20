# 三地同步方案 - 测试单元集

## 概述
本目录包含三地数据同步方案的所有**未测试/未完成功能**的测试单元。

每个测试单元都是**独立可运行**的，可以用于：
- 验证某个功能是否正常工作
- 交给不同AI模型并行测试
- 作为回归测试套件

## 测试单元列表

| 编号 | 文件名 | 测试目标 | 类型 | 依赖 |
|------|--------|----------|------|------|
| 1 | `test_01_pa_code_update.md` | PA代码更新到最新版本 | 🔴 人工 | 无 |
| 2 | `test_02_webhook_trigger.md` | GitHub Webhook触发PA同步 | 🔶 半自动 | 测试1 |
| 3 | `test_03_verify_sync.py` | 三地同步验证（运行verify_sync.py） | 🤖 自动化 | 测试2 |
| 4 | `test_04_update_data_version.py` | update_data_version.py功能测试 | 🤖 自动化 | 无 |
| 5 | `test_05_sync_script.sh` | sync_data.sh功能测试 | 🤖 自动化 | 无 |
| 6 | `test_06_safe_pull.sh` | safe_pull.sh防回滚测试 | 🤖 自动化 | 无 |
| 7 | `test_07_api_version.py` | /api/version端点测试 | 🤖 自动化 | 测试1 |
| 8 | `test_08_api_sync.py` | /api/sync端点测试 | 🤖 自动化 | 测试1 |

## 执行顺序（推荐）

### 关键路径（必须按顺序）
```
测试1 (PA代码更新)
  ↓
测试2 (GitHub Webhook触发)
  ↓
测试3 (三地同步验证)
```

### 并行测试（可在测试1完成后同时运行）
```
测试1 完成后：
  ├─ 测试4 (update_data_version.py)
  ├─ 测试5 (sync_data.sh)
  ├─ 测试6 (safe_pull.sh)
  ├─ 测试7 (api/version)
  └─ 测试8 (api/sync)
```

## 如何运行

### 自动化测试（测试3-8）
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/

# 测试3：三地同步验证
python3 task_packages/sync_test_units/test_03_verify_sync.py

# 测试4：update_data_version.py
python3 task_packages/sync_test_units/test_04_update_data_version.py

# 测试5：sync_data.sh
bash task_packages/sync_test_units/test_05_sync_script.sh

# 测试6：safe_pull.sh
bash task_packages/sync_test_units/test_06_safe_pull.sh

# 测试7：api/version
python3 task_packages/sync_test_units/test_07_api_version.py

# 测试8：api/sync
python3 task_packages/sync_test_units/test_08_api_sync.py
```

### 人工测试（测试1-2）
- **测试1**：按照 `test_01_pa_code_update.md` 中的步骤，在PA Console执行命令
- **测试2**：按照 `test_02_webhook_trigger.md` 中的步骤，推送代码并检查GitHub Webhook

## 测试通过标准

### 测试1：PA代码更新
- ✅ `git log` 显示 `7c33132` 是最新commit
- ✅ `/api/version` 返回HTTP 200

### 测试2：GitHub Webhook触发
- ✅ GitHub Webhook Delivery显示Status 200
- ✅ Response body包含 `"status": "success"`

### 测试3：三地同步验证
- ✅ `verify_sync.py` 输出中**没有** `❌` 符号
- ✅ 所有时间差 < 10分钟

### 测试4：update_data_version.py
- ✅ 三个来源（local/github/pythonanywhere）都测试通过
- ✅ `data_version.json` 的 `source` 字段正确

### 测试5：sync_data.sh
- ✅ 脚本可执行
- ✅ 能成功创建commit

### 测试6：safe_pull.sh
- ✅ 本地有更新时，阻止 `git pull`
- ✅ 提示用户先push

### 测试7：api/version
- ✅ 返回HTTP 200
- ✅ 响应包含 `version`, `source`, `etf_count`, `checksum` 字段

### 测试8：api/sync
- ✅ 返回HTTP 200
- ✅ 响应中 `status` 为 `"success"`

## 当前状态（2026-05-20 13:30）

| 测试单元 | 状态 | 说明 |
|----------|------|------|
| 测试1 | ❌ 未开始 | 需要人工在PA Console执行 |
| 测试2 | ⏳ 阻塞中 | 依赖测试1完成 |
| 测试3 | ⏳ 阻塞中 | 依赖测试2完成 |
| 测试4 | ❌ 未开始 | 可立即运行 |
| 测试5 | ❌ 未开始 | 可立即运行 |
| 测试6 | ❌ 未开始 | 可立即运行 |
| 测试7 | ❌ 未开始 | 依赖测试1完成 |
| 测试8 | ❌ 未开始 | 依赖测试1完成 |

## 建议分工

### 方案A：串行执行（适合单个模型）
1. 先完成**测试1**（人工操作）
2. 再完成**测试2-3**（验证核心流程）
3. 最后完成**测试4-8**（完善测试覆盖）

### 方案B：并行执行（适合多个模型）
1. 模型1：完成**测试1**（人工操作）
2. 模型2-6：在测试1完成后，并行运行**测试4-8**
3. 模型1：测试1完成后，继续完成**测试2-3**

## 文件清单

```
sync_test_units/
├── README.md                        # 本文件
├── test_01_pa_code_update.md       # 测试1：PA代码更新（人工）
├── test_02_webhook_trigger.md      # 测试2：Webhook触发（半自动）
├── test_03_verify_sync.py         # 测试3：三地同步验证（自动化）
├── test_04_update_data_version.py # 测试4：update_data_version（自动化）
├── test_05_sync_script.sh         # 测试5：sync_data.sh（自动化）
├── test_06_safe_pull.sh          # 测试6：safe_pull.sh（自动化）
├── test_07_api_version.py        # 测试7：api/version（自动化）
└── test_08_api_sync.py          # 测试8：api/sync（自动化）
```

## 备注

- 所有测试单元都是**独立**的，可以单独运行
- 测试1-2需要**人工操作**，无法完全自动化
- 测试3-8是**自动化测试**，可以重复运行
- 如果某个测试失败，查看对应的 `.md` 或 `.py` 文件中的"失败处理"章节
