#!/bin/bash
# PA一键部署脚本 - 解决手动多步操作导致的死循环问题
# 用法: bash pa_deploy.sh
# 或者: ./pa_deploy.sh (需要先 chmod +x pa_deploy.sh)

set -e  # 遇到错误立即退出

cd ~/etf-tool-mvp || exit 1

echo "=== PA部署开始 ==="

# Step 1: 检查并修复git remote URL (防止死循环的关键)
echo "[1/5] 检查git remote URL..."
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
EXPECTED_URL="https://github.com/froza88/etf-tool-mvp.git"

if [ "$REMOTE_URL" != "$EXPECTED_URL" ]; then
    echo "  ⚠️  Remote URL不正确: $REMOTE_URL"
    echo "  修复为: $EXPECTED_URL"
    git remote set-url origin "$EXPECTED_URL"
else
    echo "  ✓ Remote URL正确: $REMOTE_URL"
fi

# Step 2: Fetch最新代码 (必须fetch，不能只pull)
echo "[2/5] Fetch最新代码..."
git fetch origin

# Step 3: 检查是否有新提交
LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse origin/main 2>/dev/null || echo "")

if [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
    echo "  ℹ️  已是最新版本，无需更新"
    echo "  当前版本: $(git log -1 --oneline)"
else
    echo "  📥 发现新版本: $LOCAL_HASH -> $REMOTE_HASH"
    
    # Step 4: Reset到origin/main (强制同步，不合并)
    echo "[3/5] Reset到origin/main..."
    git reset --hard origin/main
    echo "  ✓ 已重置到: $(git log -1 --oneline)"
fi

# Step 5: Touch WSGI文件重载应用
echo "[4/5] Touch WSGI文件重载应用..."
touch /var/www/froza_pythonanywhere_com_wsgi.py
echo "  ✓ WSGI已重载"

# Step 6: 更新data_version.json标记PA已同步 (可选)
echo "[5/5] 更新data_version.json..."
if [ -f "update_data_version.py" ]; then
    python3 update_data_version.py --source pythonanywhere 2>/dev/null && {
        echo "  ✓ data_version.json已更新"
        # 自动commit并push回GitHub (让GitHub知道PA已同步)
        if git diff --quiet data_version.json; then
            echo "  ℹ️  data_version.json无变化，跳过push"
        else
            git add data_version.json
            git commit -m "PA: update sync_status [auto]" --quiet 2>/dev/null || echo "  ⚠️  git commit失败(可能无变化)"
            git push origin main --quiet 2>/dev/null && echo "  ✓ 已push回GitHub" || echo "  ⚠️  git push失败(可能无权限)"
        fi
    } || echo "  ⚠️  update_data_version.py失败，但部署已完成"
else
    echo "  ⚠️  update_data_version.py不存在，跳过版本标记"
fi

echo ""
echo "=== 部署完成 ==="
echo "当前版本: $(git log -1 --oneline)"
echo "WSGI已重载，应用将在下次请求时更新"
echo ""
echo "验证命令:"
echo "  curl https://froza.pythonanywhere.com/api/version"
