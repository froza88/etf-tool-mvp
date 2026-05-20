# 测试单元1：PA代码更新测试

## 测试目标
验证PythonAnywhere (PA) 上的代码是否成功更新到最新版本 `7c33132`

## 测试类型
🔴 **需要人工操作**（在PA Web UI Console执行）

## 测试步骤

### 步骤1：在PA Console执行更新命令
```bash
cd /home/froza/etf-tool-mvp/
git fetch origin main
git reset --hard origin/main
git log --oneline -3
touch /var/www/froza_pythonanywhere_com_wsgi.py
```

### 步骤2：验证更新结果
**期望输出**：
```
7c33132 fix: /api/sync 添加 git reset --hard 解决本地修改冲突
53739e7 test: webhook sync
ccbb5d8 test: 验证 webhook 自动同步
```

**成功标志**：
- ✅ `git log` 显示 `7c33132` 是最新commit
- ✅ 没有error信息

**失败处理**：
- 如果 `git fetch` 失败 → 检查网络连接
- 如果 `git reset` 失败 → 检查是否有未提交修改（先 `git stash`）
- 如果 `touch` 失败 → 检查文件路径是否正确

### 步骤3：验证/api/version端点
在浏览器访问：
```
https://froza.pythonanywhere.com/api/version
```

**期望响应**：
```json
{
  "version": "2026-05-20Txx:xx:xx.xxxxxx+08:00",
  "source": "pythonanywhere",
  "etf_count": 1468,
  "checksum": "...",
  "sync_status": {
    "github": false,
    "local": false,
    "pythonanywhere": true
  }
}
```

**成功标志**：
- ✅ `source` 字段是 `"pythonanywhere"`
- ✅ 返回HTTP 200

**失败处理**：
- 如果返回404 → PA没拿到新代码，回到步骤1
- 如果返回500 → 代码有bug，查看PA error log

## 测试交付物
- [ ] PA Console执行输出（截图或文本）
- [ ] /api/version响应（JSON文本）

## 依赖
无

## 后续测试单元
- 测试单元2：GitHub Webhook触发测试（依赖本测试成功）
