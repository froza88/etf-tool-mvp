#!/bin/bash
# 本地预处理脚本 - 更新版本清单并推送到GitHub
# 在本地运行，然后在PythonAnywhere运行 deploy.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "📊 更新版本清单并推送"
echo "=========================================="
echo ""

# Step 1: 更新版本清单
echo "[1/4] 更新版本清单..."
cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
python3 version_tracker.py
echo "✅ 版本清单已更新"
echo ""

# Step 2: 添加版本清单到git
echo "[2/4] 添加版本清单到Git..."
git add "ETF_工具MVP_完整版本清单.md"
echo "✅ 已添加到Git"
echo ""

# Step 3: 提交版本清单（如果有的话）
echo "[3/4] 检查是否需要提交..."
if git diff --cached --quiet; then
    echo "ℹ️ 版本清单无变化，跳过提交"
else
    git commit -m "docs: Update version list (auto-generated)"
    echo "✅ 已提交到本地仓库"
fi
echo ""

# Step 4: 推送到GitHub
echo "[4/4] 推送到GitHub..."
git push origin main
echo "✅ 已推送到GitHub"
echo ""

echo "=========================================="
echo "🎉 版本清单更新完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 登录 PythonAnywhere"
echo "  2. 运行: bash deploy.sh"
echo ""
