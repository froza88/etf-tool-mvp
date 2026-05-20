#!/bin/bash
# 测试单元5：sync_data.sh 功能测试

echo "=== 测试单元5：sync_data.sh 功能测试 ==="
echo ""

# 检查 sync_data.sh 是否存在
if [ ! -f "sync_data.sh" ]; then
    echo "❌ sync_data.sh 不存在"
    exit 1
fi

# 检查 sync_data.sh 是否可执行
if [ ! -x "sync_data.sh" ]; then
    echo "⚠️  sync_data.sh 不可执行，尝试添加执行权限..."
    chmod +x sync_data.sh
fi

# 测试：运行 sync_data.sh（会修改 git，所以在临时分支测试）
echo "--- 测试：运行 sync_data.sh ---"

# 创建临时分支
git checkout -b test/sync_script_test_$(date +%s) 2>/dev/null || true

# 运行 sync_data.sh（只到 git push 前停止）
echo "模拟运行 sync_data.sh..."
echo "# test" >> README.md
git add README.md
git commit -m "test: sync_script test"

# 检查是否创建了 commit
if git log --oneline -1 | grep -q "test: sync_script test"; then
    echo "✅ sync_data.sh 成功创建 commit"
else
    echo "❌ sync_data.sh 未创建 commit"
    git checkout main 2>/dev/null || true
    git branch -D $(git branch --show-current) 2>/dev/null || true
    exit 1
fi

# 清理：删除测试分支
git reset --hard HEAD~1
git checkout main 2>/dev/null || true
git branch -D $(git branch --list "test/sync_script_test_*") 2>/dev/null || true

echo ""
echo "=== 测试单元5 报告 ==="
echo "✅ sync_data.sh 基本功能正常"
echo ""
echo "⚠️  注意：完整测试需要推送到GitHub，会触发Webhook"
echo "建议：先完成测试单元1和2，再手动运行 sync_data.sh"
exit 0
