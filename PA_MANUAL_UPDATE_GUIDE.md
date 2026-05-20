# PythonAnywhere 手动更新指南（无 SSH 方案）

## 问题诊断

`https://froza.pythonanywhere.com/api/version` 返回 404，说明：
- PythonAnywhere 运行的是**旧版本代码**（`/api/version` 端点不存在）
- 需要手动触发更新

---

## 解决方案：通过 PythonAnywhere Web UI 操作

### 方案 A: 使用 PythonAnywhere "Run in console" 功能（推荐）

#### 步骤 1: 登录 PythonAnywhere
- 访问：https://www.pythonanywhere.com/
- 登录你的账号

#### 步骤 2: 打开 "Files" 标签
- 点击顶部 **"Files"** 标签
- 浏览到你的项目目录：`/home/froza/etf-tool-mvp`

#### 步骤 3: 打开 Console（控制台）
- 点击顶部 **"Consoles"** 标签
- 点击 **"Create a new console"** 或打开已有的 Bash console

#### 步骤 4: 在 Console 中执行 Git Pull
```bash
cd /home/froza/etf-tool-mvp
git pull origin main
```

**如果成功**，会看到类似输出：
```
remote: Enumerating objects: 5, done.
remote: Counting objects: 100% (5/5), done.
...
Fast-forward
```

#### 步骤 5: 重启 Web 应用（Touch WSGI）
**方法 1: 通过 Web UI**
1. 点击顶部 **"Web"** 标签
2. 找到你的应用：`froza.pythonanywhere.com`
3. 点击 **"Reload froza.pythonanywhere.com"** 按钮（绿色）

**方法 2: 在 Console 中执行**
```bash
touch /var/www/froza_pythonanywhere_com_wsgi.py
```

#### 步骤 6: 验证
在浏览器访问：`https://froza.pythonanywhere.com/api/version`

**应该看到 JSON 响应**（不再 404）

---

### 方案 B: 如果无法使用 Console（备选）

#### 使用 PythonAnywhere "Editor" 临时修改代码

**原理：** 通过 Web 编辑器临时添加 `/api/version` 端点，让接口先可用，然后再通过正常流程更新

**不推荐**，太复杂且容易出错。建议还是用方案 A。

---

### 方案 C: 检查 PythonAnywhere 是否已经自动拉取（如果配置了定时任务）

如果你之前已经配置了 PythonAnywhere 定时任务（每 10 分钟 pull），可能：
- 定时任务还没执行（刚配置完）
- 定时任务执行失败（查看日志）

#### 检查定时任务状态
1. 点击 **"Tasks"** 或 **"Schedule"** 标签
2. 查看是否有 `git pull` 任务
3. 查看任务执行历史（Last run status）

---

## 快速验证：PythonAnywhere 当前运行的是哪个版本？

### 方法：访问首页查看数据更新时间

1. 访问：https://froza.pythonanywhere.com/
2. 查看页面底部显示的数据更新时间
3. 对比本地 `data/meta.json` 中的 `last_update` 时间

**如果时间不一样** → PA 运行的是旧版本  
**如果时间一样** → PA 运行的是新版本（但 `/api/version` 还是 404，说明路由有问题）

---

## 临时方案：先不配置 Webhook，用手动同步

如果 PythonAnywhere 更新太麻烦，我们可以**暂时用手动同步方案**：

### 手动同步流程
1. 本地修改代码/数据
2. `git push origin main`
3. 登录 PythonAnywhere
4. 打开 Console
5. 执行 `git pull origin main`
6. 点击 "Reload" 按钮

**优点：** 简单直接，不需要配置 Webhook  
**缺点：** 每次都要手动操作（容易忘记）

---

## 我的建议

**优先级顺序：**

1. **先试方案 A**（通过 Console 执行 `git pull`）→ 最快
2. **如果 Console 用不了** → 试方案 C（检查定时任务）
3. **如果都不行** → 暂时用手动同步（先不配 Webhook）

---

## 现在开始操作

**你需要：**
1. 登录 PythonAnywhere
2. 打开 Console（或 Files → 找到项目）
3. 执行 `git pull origin main`
4. Reload Web 应用
5. 再测试 `https://froza.pythonanywhere.com/api/version`

**遇到问题就把错误信息/截图发给我！**
