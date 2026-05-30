#!/bin/bash
# ETF Tool MVP - 一键启动脚本
# 用于在本地启动 Flask 服务器，访问 WeStock ETF 对比工具

set -e  # 遇到错误立即退出

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "==================================="
echo "  ETF Tool MVP - 本地启动脚本"
echo "==================================="
echo ""

# 1. 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python 3"
    echo "请先安装 Python 3.8+：https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python 版本：$PYTHON_VERSION"

# 2. 检查/创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 3. 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 4. 安装/更新依赖
echo "📥 安装依赖（Flask）..."
pip install -q flask

# 5. 检查 Node.js（WeStock 脚本需要）
if ! command -v node &> /dev/null; then
    echo "⚠️  警告：未找到 Node.js，WeStock API 可能无法工作"
    echo "   如需使用 WeStock 数据，请安装 Node.js：https://nodejs.org/"
    echo "   继续启动服务器（AKShare 等功能仍可用）..."
else
    NODE_VERSION=$(node --version 2>&1)
    echo "✅ Node.js 版本：$NODE_VERSION"
fi

# 6. 启动 Flask 服务器
echo ""
echo "🚀 启动 Flask 服务器..."
echo "   访问地址：<ADDRESS_REMOVED>
echo "   按 Ctrl+C 停止服务器"
echo ""

# 自动打开浏览器（Mac）
if [[ "$OSTYPE" == "darwin"* ]]; then
    sleep 2 && open http://localhost:5000/tools/westock-compare &
fi

# 启动服务器
python app.py
