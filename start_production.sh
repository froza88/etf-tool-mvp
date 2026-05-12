#!/bin/bash
# ETF工具MVP - 生产环境启动脚本
# 用于本地生产环境测试

echo "🚀 启动ETF工具生产环境..."

# 1. 安装生产级WSGI服务器（gunicorn）
echo "📦 安装依赖..."
pip3 install gunicorn -q

# 2. 设置生产环境变量
export FLASK_ENV=production
export PYTHONUNBUFFERED=1

# 3. 使用gunicorn启动（生产级）
echo "✅ 启动gunicorn服务器..."
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp

# 启动命令：
# -w 4：4个worker进程（根据CPU核心数调整）
# -b 0.0.0.0:5000：监听所有网络接口
# -timeout 120：超时时间120秒
gunicorn -w 4 -b 0.0.0.0:5000 -timeout 120 app:app &

echo "✅ 生产环境已启动！"
echo "📱 局域网访问地址：http://192.168.1.127:5000/"
echo "🌐 如需外网访问，请配置云服务器或内网穿透"
