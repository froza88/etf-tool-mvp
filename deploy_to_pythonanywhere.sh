#!/bin/bash
# ETF工具一键部署脚本 - 自动打包并上传到PythonAnywhere
# 使用方法：
#   /bin/bash /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/deploy_to_pythonanywhere.sh
# 或简化：
#   ./deploy_to_pythonanywhere.sh

set -e  # 遇到错误立即退出

PROJECT_DIR="/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp"
DEPLOY_ZIP="$PROJECT_DIR/etf-tool-deployment.zip"
PYTHONANYWHERE_USER=""
PYTHONANYWHERE_PASS=""

echo "🚀 ETF工具自动部署脚本"
echo "================================"
echo ""

# 步骤1：检查PythonAnywhere凭据
if [ -z "$PYTHONANYWHERE_USER" ] || [ -z "$PYTHONANYWHERE_PASS" ]; then
    echo "⚠️  未配置PythonAnywhere FTP凭据"
    echo "请手动上传 $DEPLOY_ZIP 到PythonAnywhere"
    echo ""
    echo "手动上传步骤："
    echo "1. 访问 https://www.pythonanywhere.com/"
    echo "2. 登录 → Files标签 → Upload a file"
    echo "3. 选择 $DEPLOY_ZIP"
    echo "4. 勾选zip文件 → Unzip"
    echo "5. Web标签 → Reload"
    echo ""
    read -p "是否继续打包（不自动上传）？[y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 步骤2：更新ETF数据（可选）
echo "📊 步骤1：更新ETF数据..."
read -p "是否先更新ETF数据（耗时约2分钟）？[y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$PROJECT_DIR"
    /usr/bin/python3 auto_update_etf_data.py
    echo "✅ ETF数据已更新"
else
    echo "⏭️  跳过数据更新"
fi

# 步骤3：创建部署包
echo ""
echo "📦 步骤2：创建部署包..."
cd "$PROJECT_DIR"

# 删除旧包
rm -f "$DEPLOY_ZIP"

# 打包
zip -r etf-tool-deployment.zip \
    app.py \
    etf_data.py \
    etf_complete_130.json \
    requirements.txt \
    Procfile \
    templates/ \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x "*.log" \
    -x ".DS_Store"

echo "✅ 部署包已创建："
ls -lh "$DEPLOY_ZIP"
echo ""

# 步骤4：上传到PythonAnywhere（如果配置了凭据）
if [ -n "$PYTHONANYWHERE_USER" ] && [ -n "$PYTHONANYWHERE_PASS" ]; then
    echo "📤 步骤3：上传到PythonAnywhere..."
    
    # 使用lftp上传（需要先安装lftp）
    if command -v lftp &> /dev/null; then
        lftp -u "$PYTHONANYWHERE_USER,$PYTHONANYWHERE_PASS" \
            ftp://ftp.pythonanywhere.com << EOF
cd /var/www/${PYTHONANYWHERE_USER}_mysite/
put "$DEPLOY_ZIP"
bye
EOF
        echo "✅ 上传成功！"
        echo "请登录PythonAnywhere解压并重启Web应用"
    else
        echo "⚠️  未安装lftp，无法自动上传"
        echo "请手动上传："
        echo "  $DEPLOY_ZIP"
    fi
else
    echo "📤 步骤3：手动上传"
    echo "请访问 https://www.pythonanywhere.com/ 手动上传："
    echo "  $DEPLOY_ZIP"
fi

echo ""
echo "================================"
echo "✅ 部署准备完成！"
echo ""
echo "下一步："
echo "1. 上传 $DEPLOY_ZIP 到PythonAnywhere"
echo "2. 解压文件"
echo "3. 安装依赖：pip3 install --user -r requirements.txt"
echo "4. 重启Web应用：Web标签 → Reload"
echo ""
echo "测试URL："
echo "  http://${PYTHONANYWHERE_USER}.pythonanywhere.com/"
