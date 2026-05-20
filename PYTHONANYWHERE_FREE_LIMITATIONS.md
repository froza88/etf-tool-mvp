# PythonAnywhere 免费版限制与解决方案

**文档版本**: 1.0  
**创建时间**: 2026-05-20  
**适用项目**: ETF-tool-MVP (froza.pythonanywhere.com)  
**账号类型**: PythonAnywhere 免费版 (Free tier)

---

## 📋 免费版功能限制清单

| 功能 | 免费版 | 付费版 (Hacker/$5/mo) | 影响 |
|------|--------|---------------------|------|
| **Scheduled tasks** (定时任务) | ❌ 不可用 | ✅ 可用 | 无法自动定时执行脚本 |
| **Always-on tasks** (常驻任务) | ❌ 不可用 | ✅ 可用 | 后台任务会休眠 |
| **SSH 访问** | ❌ 不可用 | ✅ 可用 | 无法远程命令行操作 |
| **Web UI** (Files/Console) | ✅ 可用 | ✅ 可用 | 可以通过网页操作 |
| **自定义域名** | ❌ 不可用 | ✅ 可用 | 只能用 *.pythonanywhere.com |
| **CPU 时间** | 有限制 | 更多 | 长时间任务可能被杀 |
| **数据库** | SQLite only | PostgreSQL/MySQL | 只能用 SQLite |

---

## ⚠️ 核心限制与影响

### 限制 1: 没有 Scheduled Tasks (定时任务)

**问题描述：**
- 无法配置 cron 定时任务
- 无法实现"每 10 分钟自动执行 git pull"
- 无法自动化数据同步

**影响：**
- ❌ 不能通过定时任务实现三地自动同步
- ❌ 需要手动触发同步（登录 PA → Console → 执行命令）

**解决方案：**
1. **方案 A: GitHub Webhook** (推荐)
   - 原理：GitHub 收到 push → 自动调用 PA 的 `/api/sync` 接口
   - 优点：实时同步（push 后几秒）
   - 缺点：需要配置，可能遇到权限问题
   - 详见：[GITHUB_WEBHOOK_SETUP.md](./GITHUB_WEBHOOK_SETUP.md)

2. **方案 B: 半自动同步** (备选)
   - 原理：每次 push 后，手动登录 PA 执行 `git pull`
   - 优点：简单可靠，不需要配置
   - 缺点：容易忘记，不同步
   - 适用：开发阶段，频率不高的更新

---

### 限制 2: 没有 SSH 访问

**问题描述：**
- 无法通过 SSH 远程登录 PA 服务器
- 无法使用 `ssh user@pythonanywhere.com` 命令

**影响：**
- ❌ 不能通过脚本自动化远程操作
- ❌ 不能使用 `scp`/`rsync` 传输文件

**解决方案：**
1. **使用 Web UI Console** (推荐)
   - 登录 https://www.pythonanywhere.com/
   - 点击 "Consoles" → 打开 Bash console
   - 在网页终端中执行命令（和 SSH 体验类似）

2. **使用 Git HTTPS + Token**
   - 生成 GitHub Personal Access Token
   - 修改 remote URL: `git remote set-url origin https://<token>@github.com/...`
   - 这样 `git pull/push` 不需要 SSH key

---

### 限制 3: CPU 时间限制 (可能影响长时间任务)

**问题描述：**
- 免费版 CPU 时间有限
- 长时间运行的任务（> 5 分钟）可能被杀掉

**影响：**
- ⚠️ 数据吸收脚本（处理 1468 只 ETF）可能超时
- ⚠️ Pipeline 完整流程可能无法完成

**解决方案：**
1. **分批处理** (已实现)
   - 使用 `absorb_batch.py` 分批处理（每批 50 只）
   - 每批独立运行，避免超时

2. **后台任务 + 监控**
   - 在 Console 中运行：`nohup python3 script.py &`
   - 定期检查日志：`tail -f nohup.out`

---

## 🔧 已验证的操作方案

### 方案 1: 手动更新 PA 代码 (必须先做)

**场景：** PA 运行的是旧代码，需要更新到最新版本

**步骤：**
1. 登录 https://www.pythonanywhere.com/
2. 点击 "Consoles" → "Start a new console" → "Bash"
3. 在终端执行：
   ```bash
   cd /home/froza/ETF-tool-MVP
   git pull origin main
   ```
4. 如果提示冲突，执行：
   ```bash
   git fetch origin main
   git reset --hard origin/main
   ```
5. 点击 "Web" → 找到 `froza.pythonanywhere.com` → 点击 "Reload" 按钮
6. 验证：访问 `https://froza.pythonanywhere.com/api/version`，应该返回 JSON

**预计时间：** 5 分钟

---

### 方案 2: 配置 GitHub Webhook (推荐)

**场景：** 实现自动同步，每次 `git push` 后 PA 自动更新

**前提条件：**
- ✅ PA 已更新到最新代码（包含 `/api/sync` 端点）
- ✅ `/api/sync` 接口可访问（返回 200 不是 404）

**配置步骤：**
1. 访问：https://github.com/froza88/ETF-tool-MVP/settings/hooks
2. 点击 "Add webhook"
3. 填写：
   - **Payload URL**: `https://froza.pythonanywhere.com/api/sync`
   - **Content type**: `application/json`
   - **Events**: `Just the push event`
   - **Active**: ✅ 勾选
4. 点击 "Add webhook"

**测试方法：**
```bash
# 本地执行
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
python3 update_data_version.py --source local
git add data_version.json
git commit -m "test: webhook sync"
git push origin main
```

**验证：**
1. 回到 GitHub webhook 页面
2. 查看 "Recent deliveries"
3. 应该看到新的 delivery，状态 ✅ 绿色

**故障排查：**
- 如果 ❌ 红色：点击查看 "Response" 标签，看错误信息
- 常见错误：Timeout (PA 处理慢)、500 (代码 bug)、404 (URL 错误)

---

### 方案 3: 半自动同步 (临时方案)

**场景：** Webhook 配置太复杂，先用手动方式

**流程：**
1. 本地修改代码/数据
2. `git push origin main`
3. 登录 PythonAnywhere
4. 打开 "Consoles" → Bash console
5. 执行：`cd /home/froza/ETF-tool-MVP && git pull origin main`
6. 点击 "Web" → "Reload"

**优点：** 简单，不需要配置  
**缺点：** 容易忘记，不同步

---

## 📁 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| **GitHub Webhook 配置指南** | `GITHUB_WEBHOOK_SETUP.md` | 详细配置步骤 |
| **PA 手动更新指南** | `PA_MANUAL_UPDATE_GUIDE.md` | 通过 Web UI 更新代码 |
| **三地同步方案设计** | `task_packages/three_location_sync_design.md` | 整体架构设计 |
| **同步脚本** | `sync_data.sh` | 本地同步脚本 |
| **验证脚本** | `verify_sync.py` | 三地一致性检查 |

---

## 🎯 推荐的完整方案

**阶段 1: 立即执行（今天）**
1. ✅ 手动在 PA 上执行 `git pull`（更新代码）
2. ✅ 配置 GitHub Webhook（实现自动同步）
3. ✅ 测试完整流程（本地 push → PA 自动同步）

**阶段 2: 验证与优化（明天）**
1. 运行 `verify_sync.py` 检查三地一致性
2. 测试 `safe_pull.sh` 防回滚功能
3. 如果 Webhook 不稳定，添加监控告警

**阶段 3: 长期维护**
1. 定期检查 PA 日志（Error logs）
2. 如果 Webhook 失败超过 3 次，考虑升级到付费版
3. 或迁移到其他平台（Render、Railway、Fly.io）

---

## 💡 给其他 AI 模型的提示

**如果你是这个项目的未来 AI 助手，请注意：**

1. **PythonAnywhere 免费版限制** 是核心约束，所有自动化方案都必须考虑这个限制
2. **不能使用 SSH**、**不能配置定时任务**，只能通过 **Web UI** 或 **GitHub Webhook** 操作
3. **`/api/sync` 端点** 是关键：它允许 GitHub Webhook 触发 PA 自动拉取代码
4. **如果 PA 运行旧代码**（访问接口返回 404），必须先手动在 PA Console 执行 `git pull`
5. **相关文档** 都在项目根目录，遇到问题先读这些文档：
   - `PYTHONANYWHERE_FREE_LIMITATIONS.md` (本文档)
   - `GITHUB_WEBHOOK_SETUP.md`
   - `PA_MANUAL_UPDATE_GUIDE.md`

**常见错误：**
- ❌ 尝试配置 PA 定时任务 → 免费版不支持
- ❌ 尝试用 SSH 连接 PA → 免费版不支持
- ❌ 假设 `/api/sync` 一定存在 → PA 可能运行旧代码，需要先更新
- ❌ 忽略 Webhook 配置 → 无法自动同步，每次都要手动操作

---

## 📝 更新记录

| 日期 | 版本 | 更新内容 | 更新人 |
|------|------|----------|--------|
| 2026-05-20 | 1.0 | 初始版本，记录免费版限制与解决方案 | Qi (交付总监) |

---

**文档结束**
