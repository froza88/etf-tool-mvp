# PythonAnywhere 手动更新指南（优化版）

## ⚠️ 重要：不要使用 `git pull`

**经验教训（2026-05-21）**：手动执行 `git pull` 容易导致死循环，因为：
- PA的 `origin` URL 可能过时（例如仓库重命名后）
- `git pull` 会比对过时的 remote ref，一直说 "Already up to date"
- 诊断过程碎片化，来回多轮才能发现问题

**正确做法**：使用 `pa_deploy.sh` 一键部署脚本（推荐）或手动执行 `git reset --hard origin/main`

---

## 推荐方案：使用 `pa_deploy.sh` 一键部署

### 步骤 1: 登录 PythonAnywhere
- 访问：https://www.pythonanywhere.com/
- 登录你的账号

### 步骤 2: 打开 Console
- 点击顶部 **"Consoles"** 标签
- 点击 **"Create a new console"** 或打开已有的 Bash console

### 步骤 3: 运行一键部署脚本
```bash
cd ~/etf-tool-mvp
bash pa_deploy.sh
```

**脚本会自动完成：**
1. ✅ 检查并修复 git remote URL（防止死循环）
2. ✅ `git fetch origin`（获取最新代码）
3. ✅ `git reset --hard origin/main`（强制同步，不合并）
4. ✅ `touch /var/www/froza_pythonanywhere_com_wsgi.py`（重载应用）
5. ✅ `python3 update_data_version.py --source pythonanywhere`（标记PA已同步）
6. ✅ 自动 commit 并 push 回 GitHub（让GitHub知道PA已同步）

### 步骤 4: 验证部署
在浏览器访问：`https://froza.pythonanywhere.com/api/version`

**应该看到 JSON 响应**，例如：
```json
{
  "version": "2026-05-21T00:30:02+08:00",
  "source": "pythonanywhere",
  "sync_status": {
    "local": true,
    "github": true,
    "pythonanywhere": true
  }
}
```

---

## 备选方案：手动执行（如果不想用脚本）

### 正确的手动步骤（避免死循环）

```bash
cd ~/etf-tool-mvp

# 1. 检查 git remote URL（关键！）
git remote -v
# 应该显示: https://github.com/apangduo/etf-tool-mvp.git
# 如果不是，执行: git remote set-url origin https://github.com/apangduo/etf-tool-mvp.git

# 2. Fetch 最新代码（必须 fetch，不能只 pull）
git fetch origin

# 3. 检查 origin/main 是否有新提交
git log HEAD..origin/main --oneline

# 4. 如果有新提交，reset 到 origin/main（强制同步）
git reset --hard origin/main

# 5. Touch WSGI 文件重载应用
touch /var/www/froza_pythonanywhere_com_wsgi.py

# 6. 验证
git log -1 --oneline
```

### ❌ 错误的手动步骤（导致死循环）

```bash
# ❌ 不要这样做！
git pull origin main  # 如果 remote URL 过时，会一直说 "Already up to date"
```

---

## 快速验证：PythonAnywhere 当前运行的是哪个版本？

### 方法 1: 访问 `/api/version` 接口
在浏览器访问：`https://froza.pythonanywhere.com/api/version`

**如果返回 JSON** → PA 运行的是新版本  
**如果返回 404** → PA 运行的是旧版本（缺少 `/api/version` 端点）

### 方法 2: 访问首页查看数据更新时间
1. 访问：https://froza.pythonanywhere.com/
2. 查看页面底部显示的数据更新时间
3. 对比本地 `data/meta.json` 中的 `last_update` 时间

**如果时间不一样** → PA 运行的是旧版本  
**如果时间一样** → PA 运行的是新版本

---

## 故障排查

### 问题 1: `pa_deploy.sh` 说 "已是最新版本，无需更新"
**原因**：本地已经是最新版本  
**解决**：检查 GitHub 上是否有新提交。如果没有，说明无需更新。

### 问题 2: `git reset --hard origin/main` 后版本不对
**原因**：`origin/main` 指向的提交不是最新的  
**解决**：
```bash
git fetch origin  # 再次 fetch
git log origin/main --oneline -3  # 检查 origin/main 是否正确
git reset --hard origin/main  # 再次 reset
```

### 问题 3: Touch WSGI 后应用没更新
**原因**：WSGI 文件重载有延迟（几秒到几十秒）  
**解决**：等待 30 秒后再验证，或手动在 Web UI 点击 "Reload" 按钮

---

## 我的建议

**优先级顺序：**

1. **首选：`pa_deploy.sh` 一键部署** → 最简单，防死循环
2. **备选：手动执行正确步骤** → 如果脚本出问题，按"正确的手动步骤"操作
3. **禁止：使用 `git pull`** → 容易导致死循环

---

## 现在开始操作

**你需要：**
1. 登录 PythonAnywhere
2. 打开 Console
3. 执行 `cd ~/etf-tool-mvp && bash pa_deploy.sh`
4. 等待脚本完成（约 10-30 秒）
5. 验证 `https://froza.pythonanywhere.com/api/version`

**遇到问题就把错误信息/截图发给我！**
