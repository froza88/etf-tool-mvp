#!/bin/bash
#########################################
# PythonAnywhere Git 一键部署脚本
# 使用方法：
#   1. 在 PythonAnywhere Bash 中执行：
#      bash <(curl -s https://raw.githubusercontent.com/froza88/ETF-tool-MVP/main/deploy.sh)
#   2. 或者下载后执行：
#      source deploy.sh
#########################################

set -e  # 遇到错误立即退出

# ========== 配置区 ==========
REPO_URL="https://github.com/froza88/ETF-tool-MVP.git"
BRANCH="main"
TARGET_DIR="/home/froza/mysite"
BACKUP_DIR="$TARGET_DIR/backup_$(date +%Y%m%d_%H%M%S)"
# =============================

echo "=========================================="
echo "🚀 PythonAnywhere Git 部署脚本"
echo "=========================================="
echo "仓库: $REPO_URL"
echo "分支: $BRANCH"
echo "目标: $TARGET_DIR"
echo "=========================================="
echo ""

# 检查目录
if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ 目录不存在: $TARGET_DIR"
    exit 1
fi

cd "$TARGET_DIR"

# 步骤1：备份
echo "📦 步骤1: 备份现有文件..."
mkdir -p "$BACKUP_DIR"
if ls *.py *.json *.html requirements.txt 2>/dev/null; then
    cp *.py *.json *.html requirements.txt "$BACKUP_DIR/" 2>/dev/null || true
    cp -r templates/ "$BACKUP_DIR/" 2>/dev/null || true
    echo "  ✅ 备份到: $BACKUP_DIR"
else
    echo "  ⚠️  没有文件需要备份"
fi

# 步骤2：拉取/克隆代码
echo ""
echo "📤 步骤2: 获取最新代码..."

if [ -d ".git" ]; then
    echo "  检测到 Git 仓库，执行 git pull..."
    git pull origin $BRANCH
else
    echo "  清理目录并克隆仓库..."
    # 删除所有文件（保留隐藏文件和目录）
    find . -maxdepth 1 -type f -delete
    find . -maxdepth 1 -type d ! -name "." ! -name ".*" -exec rm -rf {} +
    
    echo "  克隆仓库..."
    git clone "$REPO_URL" temp_deploy
    mv temp_deploy/* . 2>/dev/null || true
    mv temp_deploy/.git . 2>/dev/null || true
    rm -rf temp_deploy
fi

echo "  ✅ 代码已更新"

# 步骤3：安装依赖
echo ""
echo "📦 步骤3: 安装 Python 依赖..."

if [ -f "requirements.txt" ]; then
    pip3 install --user -r requirements.txt
    echo "  ✅ 依赖已安装"
else
    echo "  ⚠️  未找到 requirements.txt"
fi

# 步骤4：验证
echo ""
echo "✅ 步骤4: 验证部署..."
echo ""
echo "Python 文件:"
ls -lh *.py 2>/dev/null | head -10

echo ""
echo "JSON 数据文件:"
ls -lh *.json 2>/dev/null | head -5

echo ""
echo "模板目录:"
ls -d templates/ 2>/dev/null && ls templates/*.html 2>/dev/null

# 完成
echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 访问: https://www.pythonanywhere.com/webapps/"
echo "2. 点击 'Reload froza.pythonanywhere.com'"
echo ""
echo "🌐 然后访问: https://froza.pythonanywhere.com"
echo "=========================================="
