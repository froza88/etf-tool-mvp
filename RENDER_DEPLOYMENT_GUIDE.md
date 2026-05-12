# ETF筛选器 - Render云部署指南

## 🚀 快速部署（3步搞定）

### 第一步：推送到GitHub

1. **登录GitHub**，创建新仓库：
   - 访问 https://github.com/new
   - 仓库名：`etf-screener`
   - 选择 **Public**
   - 不要勾选 "Initialize this repository with a README"
   - 点击 "Create repository"

2. **在终端执行**（复制GitHub给你的命令）：
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
git remote add origin https://github.com/你的用户名/etf-screener.git
git branch -M main
git push -u origin main
```

### 第二步：部署到Render

1. **登录Render**：https://render.com （用GitHub账号登录更快）

2. **点击 "New +" → "Web Service"**

3. **连接GitHub仓库**：
   - 选择 `etf-screener` 仓库
   - 点击 "Connect"

4. **配置服务**：
   - **Name**: `etf-screener`（或自定义）
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: 选择 **Free**

5. **点击 "Create Web Service"**

### 第三步：等待部署完成

- Render会自动构建和部署（约2-5分钟）
- 部署成功后，你会获得一个网址：
  ```
  https://etf-screener.onrender.com
  ```

✅ **完成！** 现在你可以在手机/电脑上访问这个网址了！

---

## 📱 手机访问

部署成功后，在手机浏览器输入：
```
https://etf-screener.onrender.com
```

**注意**：
- Free版会有冷启动（15分钟无访问会休眠，下次访问需要等待30秒唤醒）
- 如果觉得慢，可以升级到付费版（$7/月）

---

## 🔄 后续更新代码

每次修改代码后，只需要：
```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
git add .
git commit -m "更新说明"
git push
```
Render会自动重新部署！

---

## 🆘 常见问题

### Q1: GitHub推送失败怎么办？
**A**: 需要配置GitHub认证，推荐使用Personal Access Token：
1. GitHub → Settings → Developer settings → Personal access tokens → Generate new token
2. 复制token，推送时用token替代密码

### Q2: Render部署失败怎么办？
**A**: 检查：
- `requirements.txt` 是否存在
- `Procfile` 是否存在（内容：`web: gunicorn app:app`）
- 查看Render的部署日志（Dashboard → 你的服务 → Logs）

### Q3: 免费版休眠怎么办？
**A**: 有多个选择：
1. 忍受冷启动（个人测试够用）
2. 升级付费版（$7/月，永不休眠）
3. 使用其他免费平台（Vercel、Fly.io等）

---

## 📊 部署检查清单

- [ ] 代码已推送到GitHub
- [ ] Render服务已创建
- [ ] 部署状态显示 "Live"
- [ ] 访问网址能看到ETF筛选器首页
- [ ] 筛选功能正常工作
- [ ] 详情页能正常打开

---

## 🎉 部署成功后的下一步

1. **自定义域名**（可选）：
   - 在Render Dashboard → Settings → Custom Domains
   - 添加你的域名（如 `etf.yourdomain.com`）

2. **添加数据库**（如果需要）：
   - Render提供免费PostgreSQL（但有容量限制）
   - 或连接外部数据库

3. **监控和分析**：
   - Render提供基础访问日志
   - 可集成Google Analytics

---

**需要帮助？**
- Render文档：https://render.com/docs
- 或问我，我帮你调试！
