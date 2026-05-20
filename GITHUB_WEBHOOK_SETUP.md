# GitHub Webhook 配置指南 - 自动触发 PythonAnywhere 同步

## 目标
每次 `git push` 到 GitHub 后，自动触发 PythonAnywhere 执行 `git pull`，实现三地数据同步。

## 配置步骤（无需 SSH）

### 步骤 1: 在 PythonAnywhere 上准备接口

**问题：** `/api/sync` 端点需要能从外网访问。

**当前状态：** 
- PythonAnywhere 免费版域名：`froza.pythonanywhere.com`
- `/api/sync` 端点已存在（app.py 第 490 行）
- 需要验证接口是否可访问

**验证方法：**
1. 在浏览器访问：`https://froza.pythonanywhere.com/api/version`
2. 应该看到 JSON 响应（包含 version、source、checksum 等）
3. 如果看到 404 或 500 错误，说明接口有问题

---

### 步骤 2: 在 GitHub 上配置 Webhook

#### 2.1 登录 GitHub
- 访问：https://github.com/froza88/ETF-tool-MVP
- 点击右上角你的头像 → Settings

#### 2.2 进入仓库设置
- 或者直接访问：https://github.com/froza88/ETF-tool-MVP/settings/hooks
- 点击 **"Add webhook"** 按钮

#### 2.3 填写 Webhook 配置

| 字段 | 值 | 说明 |
|------|-----|------|
| **Payload URL** | `https://froza.pythonanywhere.com/api/sync` | PythonAnywhere 的同步接口 |
| **Content type** | `application/json` | JSON 格式 |
| **Secret** | _(留空或设置密钥)_ | 可选，用于验证请求来源 |
| **SSL verification** | _Enable_ | 保持默认 |
| **Events** | **Just the push event** | 只在 push 时触发 |
| **Active** | ✅ 勾选 | 启用 webhook |

**详细填写：**
1. **Payload URL**: 输入 `https://froza.pythonanywhere.com/api/sync`
2. **Content type**: 选择 `application/json`
3. **Secret**: 留空（或输入一个秘密字符串，后面需要在 PA 代码里验证）
4. **Events**: 选择 **"Just the push event"** (只选中 "Push" 事件)
5. **Active**: 确保勾选
6. 点击 **"Add webhook"** 按钮

#### 2.4 验证 Webhook

添加成功后：
1. GitHub 会显示一个绿色对勾 ✅ 或红色叉号 ❌
2. 点击 webhook 名称，查看 "Recent Deliveries"
3. 应该能看到一次测试请求（GitHub 会自动发送 ping）
4. 如果显示 ❌，查看 "Response" 标签，看错误信息

---

### 步骤 3: 测试完整流程

#### 3.1 本地修改并推送
```bash
# 在本地执行
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp

# 随便改点东西（比如更新版本号）
python3 update_data_version.py --source local

# 提交并推送
git add data_version.json
git commit -m "test: webhook sync test"
git push origin main
```

#### 3.2 检查 GitHub Webhook 状态
1. 访问：https://github.com/froza88/ETF-tool-MVP/settings/hooks
2. 点击你的 webhook
3. 查看 "Recent Deliveries"
4. 应该能看到一个新的 delivery（对应刚才的 push）
5. 点击查看详情：
   - **Request**: GitHub 发送的内容
   - **Response**: PythonAnywhere 返回的内容
   - 应该看到 `"status": "success"`

#### 3.3 验证 PythonAnywhere 是否已同步
**方法 A: 通过 API 检查版本**
```bash
# 在本地执行
curl https://froza.pythonanywhere.com/api/version
```
应该看到版本号已更新（和本地 `data_version.json` 的 version 字段一致）

**方法 B: 通过浏览器访问网站**
- 访问：https://froza.pythonanywhere.com/
- 查看页面底部的数据更新时间
- 应该已更新为最新时间

---

### 常见问题排查

#### 问题 1: Webhook 显示 ❌ (失败)

**查看错误：**
1. 在 GitHub webhook 页面，点击失败的 delivery
2. 查看 "Response" 标签
3. 常见错误：
   - **Timeout (超时)**: PA 处理太慢，GitHub 等待超过 10 秒
   - **500 Internal Server Error**: PA 代码有 bug
   - **404 Not Found**: URL 路径错误

**解决方案：**
- 如果是超时：优化 `/api/sync` 代码，让它快速返回（不等待 git pull 完成）
- 如果是 500 错误：检查 PA 日志（PythonAnywhere 控制台）

#### 问题 2: PythonAnywhere 没同步

**可能原因：**
1. Webhook 没触发（检查 GitHub "Recent Deliveries"）
2. `/api/sync` 执行失败（检查 PA 日志）
3. `git pull` 失败（可能冲突或权限问题）

**排查步骤：**
1. 手动访问 `https://froza.pythonanywhere.com/api/sync` (POST 请求)
   - 可以用 `curl` 或 Postman 测试
2. 检查 PA 日志：
   - 登录 PythonAnywhere
   - 打开 "Web" 标签
   - 查看 "Error logs"

#### 问题 3: Git Pull 失败（权限问题）

**症状：** `/api/sync` 返回错误，说 `git pull` 失败

**原因：** PythonAnywhere 上的 Git 没有权限 pull（需要 SSH key 或 token）

**解决方案：**
1. **使用 HTTPS + token**（推荐）
   - 在 GitHub 生成 Personal Access Token
   - 修改 PA 上的 remote URL：
     ```bash
     git remote set-url origin https://<token>@github.com/froza88/ETF-tool-MVP.git
     ```
   
2. **或者使用 SSH key**
   - 在 PA 上生成 SSH key
   - 添加到 GitHub 账号

---

### 备选方案：PythonAnywhere 定时任务（如果 Webhook 不工作）

如果 Webhook 配置太复杂或有问题，可以用 **PythonAnywhere 定时任务**：

#### 配置方法（通过 Web UI，无需 SSH）

1. **登录 PythonAnywhere**
   - 访问：https://www.pythonanywhere.com/
   
2. **打开 "Tasks" 标签**
   - 点击顶部 "Tasks" 或 "Schedule"
   
3. **添加定时任务**
   - **Command**: 
     ```bash
     cd /home/froza/ETF-tool-MVP && git pull origin main
     ```
   - **Hour**: `*/10` (每 10 分钟)
   - **Minute**: `0` (整点)
   - 或者更简单的：**Every 10 minutes**
   
4. **保存任务**

**优点：**
- 配置简单（Web UI 操作）
- 不依赖 GitHub Webhook
- 更稳定（即使 webhook 失败，10 分钟后也会同步）

**缺点：**
- 不是实时的（最多延迟 10 分钟）
- 浪费资源（即使没更新也会 pull）

---

## 推荐方案选择

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **GitHub Webhook** | 实时同步（push 后立即触发） | 配置稍复杂，需要调试 | ⭐⭐⭐⭐⭐ |
| **PA 定时任务** | 配置简单，稳定可靠 | 不是实时（最多延迟 10 分钟） | ⭐⭐⭐⭐ |
| **手动触发** | 最简单 | 容易忘记，不同步 | ⭐ |

**我的建议：**
1. **先试 GitHub Webhook**（实时性好）
2. **如果配置遇到问题，改用 PA 定时任务**（稳定可靠）
3. **两者都配置**（Webhook 实时 + 定时任务兜底）

---

## 下一步

你想先试哪个方案？

**选项 A**: 我帮你配置 GitHub Webhook（我写详细步骤 + 你照着操作）  
**选项 B**: 我帮你配置 PA 定时任务（更简单，Web UI 操作）  
**选项 C**: 我先优化 `/api/sync` 接口（让它更健壮，支持 webhook）

告诉我你的选择，或者如果有其他问题！
