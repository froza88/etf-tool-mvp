#!/bin/bash
# 测试单元6：safe_pull.sh 防回滚测试

echo "=== 测试单元6：safe_pull.sh 防回滚测试 ==="
echo ""

# 检查 safe_pull.sh 是否存在
if [ ! -f "safe_pull.sh" ]; then
    echo "❌ safe_pull.sh 不存在"
    exit 1
fi

# 创建临时测试目录
TEST_DIR="/tmp/test_safe_pull_$(date +%s)"
mkdir -p $TEST_DIR
cd $TEST_DIR

# 初始化 git 仓库
git init
echo "v1" > data_version.json
git add .
git commit -m "v1"

# 创建"远程"分支（模拟 GitHub）
git checkout -b origin_main
echo "v2" > data_version.json
git add .
git commit -m "v2 (remote)"
git checkout main

# 测试场景1：本地更新，应该提示先push
echo "--- 测试场景1：本地有更新，git pull 应该被阻止 ---"
echo "v1_local" > data_version.json
git add data_version.json

# 运行 safe_pull.sh（应该提示错误）
../safe_pull.sh 2>&1 | tee /tmp/safe_pull_test_output.txt
if grep -q "本地版本更新" /tmp/safe_pull_test_output.txt; then
    echo "✅ 场景1通过：safe_pull.sh 正确阻止了 git pull"
else
    echo "❌ 场景1失败：safe_pull.sh 未阻止 git pull"
fi

# 清理
cd /
rm -rf $TEST_DIR
rm -f /tmp/safe_pull_test_output.txt

echo ""
echo "=== 测试单元6 报告 ==="
echo "⚠️  部分测试完成（需要更完整的测试）"
echo ""
echo "建议：手动测试 safe_pull.sh 在各种场景下的行为"
exit 0
