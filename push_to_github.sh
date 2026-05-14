#!/bin/bash
# GitHub推送脚本 - 在GitHub上创建仓库后运行此脚本

echo "🚀 ETF工具MVP - GitHub推送脚本"
echo "================================"
echo ""
echo "📋 请先完成以下步骤："
echo "1. 访问 https://github.com/new"
echo "2. 创建名为 'etf-tool-mvp' 的仓库（不要勾选Initialize with README）"
echo "3. 复制仓库URL（类似：https://github.com/froza/etf-tool-mvp.git）"
echo ""
read -p "请输入GitHub仓库URL: " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "❌ 错误：URL不能为空"
    exit 1
fi

echo ""
echo "📤 添加远程仓库并推送..."
cd "$(dirname "$0")"
git remote remove origin 2>/dev/null
git remote add origin "$REPO_URL"
git branch -M main
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 成功！代码已推送到GitHub"
    echo "🔗 访问: $REPO_URL"
else
    echo ""
    echo "❌ 推送失败，可能原因："
    echo "   1. 网络连接问题"
    echo "   2. 仓库URL错误"
    echo "   3. 需要先创建仓库"
    echo ""
    echo "💡 提示：如果使用HTTPS，可能需要输入GitHub用户名和密码"
    echo "   建议使用Personal Access Token (PAT)作为密码"
fi
