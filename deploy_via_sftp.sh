#!/bin/bash
#########################################
# PythonAnywhere SFTP 自动化部署脚本
# 使用系统内置 sftp 命令，无需安装额外库
#########################################

# ========== 配置区 ==========
USERNAME="froza"
API_TOKEN="10188c344dc864597808b5744f37f5cb10e380ee"
LOCAL_DIR="/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp"
REMOTE_DIR="/home/froza/mysite"

# SFTP 服务器
SFTP_HOST="ssh.pythonanywhere.com"
SFTP_USER="$USERNAME"
# =============================

echo "=========================================="
echo "🚀 PythonAnywhere SFTP 部署脚本"
echo "=========================================="
echo "用户: $USERNAME"
echo "域名: $USERNAME.pythonanywhere.com"
echo "本地目录: $LOCAL_DIR"
echo "远程目录: $REMOTE_DIR"
echo "=========================================="
echo ""

# 检查本地目录
if [ ! -d "$LOCAL_DIR" ]; then
    echo "❌ 本地目录不存在: $LOCAL_DIR"
    exit 1
fi

# 创建临时 SFTP 批处理文件
SFTP_BATCH=$(mktemp)
trap "rm -f $SFTP_BATCH" EXIT

echo "📤 准备上传文件..."

# 添加 SFTP 命令到批处理文件
{
    echo "cd $REMOTE_DIR"
    
    # 上传根目录的 .py 文件
    for f in "$LOCAL_DIR"/*.py; do
        if [ -f "$f" ]; then
            filename=$(basename "$f")
            # 跳过测试文件
            if [[ ! "$filename" =~ ^test_ ]] && [[ ! "$filename" =~ ^auto_update ]]; then
                echo "put \"$f\" \"$filename\""
            fi
        fi
    done
    
    # 上传 JSON 文件
    for f in "$LOCAL_DIR"/*.json; do
        if [ -f "$f" ]; then
            filename=$(basename "$f")
            echo "put \"$f\" \"$filename\""
        fi
    done
    
    # 上传 requirements.txt
    if [ -f "$LOCAL_DIR/requirements.txt" ]; then
        echo "put \"$LOCAL_DIR/requirements.txt\" \"requirements.txt\""
    fi
    
    # 创建 templates 目录并上传 HTML 文件
    echo "mkdir templates"
    echo "cd templates"
    
    if [ -d "$LOCAL_DIR/templates" ]; then
        for f in "$LOCAL_DIR/templates"/*.html; do
            if [ -f "$f" ]; then
                filename=$(basename "$f")
                echo "put \"$f\" \"$filename\""
            fi
        done
    fi
    
    echo "bye"
} > "$SFTP_BATCH"

echo "📋 SFTP 批处理文件已创建: $SFTP_BATCH"
echo ""
echo "⚠️  需要你输入 PythonAnywhere 密码（API Token 不能用于 SFTP）"
echo ""
echo "如果不确定密码，请访问: https://www.pythonanywhere.com/accounts/password/reset/"
echo ""
echo "按 Enter 继续，或 Ctrl+C 取消..."
read

# 执行 SFTP 上传
echo "🚀 开始上传..."
sftp -oBatchMode=no -b "$SFTP_BATCH" "$SFTP_USER@$SFTP_HOST"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 文件上传成功！"
    echo "=========================================="
    echo ""
    echo "📦 下一步：安装依赖并重新加载 Web 应用"
    echo ""
    echo "1. 访问: https://www.pythonanywhere.com/consoles/"
    echo "2. 启动 Bash 控制台"
    echo "3. 执行以下命令:"
    echo "   cd $REMOTE_DIR"
    echo "   pip3 install --user -r requirements.txt"
    echo ""
    echo "4. 访问: https://www.pythonanywhere.com/webapps/"
    echo "5. 点击 'Reload $USERNAME.pythonanywhere.com'"
    echo ""
    echo "🌐 完成后访问: https://$USERNAME.pythonanywhere.com"
    echo "=========================================="
else
    echo ""
    echo "❌ SFTP 上传失败"
    echo ""
    echo "可能的原因:"
    echo "1. 密码错误"
    echo "2. SSH 密钥未配置"
    echo "3. 网络连接问题"
    echo ""
    echo "建议: 使用 Web 界面手动上传（最简单）"
    echo "=========================================="
    exit 1
fi
