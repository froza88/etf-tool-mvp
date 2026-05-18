#!/bin/bash
# ETF工具一键部署脚本
# 用法：在 PythonAnywhere Bash Console 中运行：bash deploy.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🚀 ETF工具一键部署"
echo "=========================================="
echo ""

# Step 1: 拉取最新代码
echo "[1/5] 拉取最新代码..."
cd ~/ETF-tool-MVP
git pull origin main
echo "✅ 代码已更新"
echo ""

# Step 2: 清理空文件（如果有）
echo "[2/5] 清理临时文件..."
if [ -f "v" ]; then
    rm v
    echo "✅ 删除空文件 v"
fi
echo ""

# Step 3: 检查关键文件是否存在
echo "[3/5] 检查数据文件..."
if [ ! -f "etf_standard_data.json" ]; then
    echo "⚠️ 警告：etf_standard_data.json 不存在，可能需要手动运行 build_standard_data.py"
fi
echo "✅ 文件检查完成"
echo ""

# Step 4: 触发 WSGI 重载
echo "[4/5] 触发 PythonAnywhere 重载..."
touch /var/www/froza_pythonanywhere_com_wsgi.py
echo "✅ WSGI 已重载"
echo ""

# Step 5: 验证部署
echo "[5/5] 验证部署..."
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://froza.pythonanywhere.com/)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ 网站响应正常 (HTTP 200)"
else
    echo "⚠️ 网站响应异常 (HTTP $HTTP_CODE)"
fi
echo ""

echo "=========================================="
echo "🎉 部署完成！"
echo "=========================================="
echo ""
echo "请访问验证："
echo "  - 首页: https://froza.pythonanywhere.com/"
echo "  - 详情页: https://froza.pythonanywhere.com/detail/510300"
echo "  - 风险页: https://froza.pythonanywhere.com/risk/510300"
echo ""
echo "验证清单："
echo "  □ 首页显示'数据更新时间'"
echo "  □ 详情页走势图显示'[真实数据]'"
echo "  □ 对比页雷达图正常显示"
echo "  □ 风险页支持1Y/2Y/3Y/5Y切换"
echo ""
