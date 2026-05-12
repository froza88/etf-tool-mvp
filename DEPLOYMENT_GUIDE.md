# ETF工具MVP - 云服务器部署指南

## 🌐 目标
让ETF工具可以从**任何地方访问**（包括WorkBuddy小程序）。

---

## 方案一：Oracle Cloud 免费层（推荐，完全免费）

### 优势：
- ✅ **永久免费**（4核CPU + 24GB内存 + 200GB存储）
- ✅ 固定公网IP
- ✅ 无时间限制

### 部署步骤：

#### 1. 注册Oracle Cloud账号
- 访问：https://www.oracle.com/cloud/free/
- 需要信用卡验证（不会扣费）
- 选择"Always Free"套餐

#### 2. 创建Ubuntu实例
- 操作系统：Ubuntu 22.04 LTS
- 规格：VM.Standard.E2.1.Micro（免费层）
- 网络：创建新的VPC和子网
- 添加入站规则：开放端口5000（TCP）

#### 3. SSH连接到服务器
```bash
ssh ubuntu@<你的公网IP>
```

#### 4. 安装依赖
```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Python3和pip
sudo apt install python3 python3-pip python3-venv -y

# 安装Nginx（反向代理）
sudo apt install nginx -y
```

#### 5. 上传ETF工具代码
**方法A：使用SCP（从本地上传）**
```bash
# 在本地电脑运行：
scp -r /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp ubuntu@<公网IP>:~/etf-tool-mvp
```

**方法B：使用Git（推荐）**
```bash
# 在服务器上：
git clone <你的Git仓库URL>
```

#### 6. 配置Python虚拟环境
```bash
cd ~/etf-tool-mvp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

创建 `requirements.txt`：
```bash
# 在本地创建
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
echo "flask" > requirements.txt
echo "gunicorn" >> requirements.txt
```

#### 7. 使用Gunicorn启动（生产级）
```bash
# 在服务器上：
cd ~/etf-tool-mvp
gunicorn -w 4 -b 0.0.0.0:5000 app:app &
```

#### 8. 配置Nginx反向代理（可选，推荐）
```bash
# 创建Nginx配置文件
sudo nano /etc/nginx/sites-available/etf-tool
```

添加以下内容：
```nginx
server {
    listen 80;
    server_name <你的公网IP>;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/etf-tool /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 9. 访问
在浏览器中输入：`http://<你的公网IP>/`

✅ 现在任何地方都能访问了！

---

## 方案二：腾讯云轻量服务器（国内速度快）

### 优势：
- ✅ 国内访问速度快
- ✅ 便宜（约￥30/月）
- ✅ 简单易用

### 部署步骤：

#### 1. 购买服务器
- 访问：https://cloud.tencent.com/product/lighthouse
- 选择：Ubuntu 22.04 / 2核4G / 5Mbps带宽
- 价格：约￥30/月

#### 2-9. 后续步骤同Oracle Cloud
（SSH连接 → 安装依赖 → 上传代码 → 启动服务）

---

## 方案三：使用Heroku（免费，但已停止新用户注册）

❌ Heroku已停止免费层，不推荐。

---

## 📋 部署检查清单

- [ ] 选择云服务器方案
- [ ] 注册账号并创建实例
- [ ] 配置安全组（开放端口5000）
- [ ] SSH连接到服务器
- [ ] 安装Python3、pip、Nginx
- [ ] 上传ETF工具代码
- [ ] 安装Python依赖（Flask、Gunicorn）
- [ ] 启动Gunicorn
- [ ] 配置Nginx反向代理（可选）
- [ ] 测试公网访问

---

## 🔒 安全建议

1. **不要使用`debug=True`**（生产环境）
   - 修改 `app.py` 最后一行：
   ```python
   if __name__ == '__main__':
       app.run(host='0.0.0.0', port=5000)
   ```

2. **使用环境变量存储敏感信息**
   - 不要硬编码密钥、Token等

3. **配置HTTPS（可选）**
   - 使用Let's Encrypt免费SSL证书
   - 命令：`sudo certbot --nginx -d <你的域名>`

---

## 💡 快速测试：本地模拟生产环境

如果暂时不想部署到云服务器，可以先在**本地模拟生产环境**：

```bash
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

然后在同一Wi-Fi下的手机访问：`http://192.168.1.127:5000/`

---

## 📞 需要帮助？

如果在部署过程中遇到问题，告诉我：
1. 选择的云服务器方案
2. 遇到的错误信息
3. 已完成的步骤

我会帮你解决！
