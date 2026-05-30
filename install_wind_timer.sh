#!/bin/bash
# Wind数据下载定时任务安装脚本
# 功能：每天早上8点自动运行Wind ETF数据下载
# 作者：WorkBuddy AI
# 日期：2026-05-31

set -e

PLIST_SOURCE="/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/com.etf-tool.wind-download.plist"
PLIST_TARGET="$HOME/Library/LaunchAgents/com.etf-tool.wind-download.plist"
LOG_DIR="$HOME/WorkBuddy/Claw/etf-tool-mvp/logs"

echo "=== Wind数据下载定时任务安装 ==="
echo ""

# 1. 检查源文件是否存在
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ 错误：plist源文件不存在: $PLIST_SOURCE"
    exit 1
fi
echo "✅ plist源文件存在: $PLIST_SOURCE"

# 2. 创建日志目录
mkdir -p "$LOG_DIR"
echo "✅ 日志目录已创建: $LOG_DIR"

# 3. 复制plist到LaunchAgents目录
cp "$PLIST_SOURCE" "$PLIST_TARGET"
echo "✅ plist已复制到: $PLIST_TARGET"

# 4. 检查是否已经加载（如果已加载，先卸载）
if launchctl list | grep -q "com.etf-tool.wind-download"; then
    echo "⚠️  任务已加载，先卸载..."
    launchctl unload "$PLIST_TARGET"
    echo "✅ 已卸载旧任务"
fi

# 5. 加载plist文件
launchctl load "$PLIST_TARGET"
echo "✅ 定时任务已加载"

# 6. 验证加载状态
echo ""
echo "=== 验证加载状态 ==="
if launchctl list | grep -q "com.etf-tool.wind-download"; then
    echo "✅ 定时任务加载成功！"
    launchctl list | grep "com.etf-tool.wind-download"
else
    echo "❌ 定时任务加载失败"
    exit 1
fi

# 7. 显示任务信息
echo ""
echo "=== 定时任务信息 ==="
echo "任务标签: com.etf-tool.wind-download"
echo "执行时间: 每天早上 8:00"
echo "执行脚本: /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/download_wind_full_data.py"
echo "标准输出日志: $LOG_DIR/wind_download_out.log"
echo "错误输出日志: $LOG_DIR/wind_download_err.log"
echo ""
echo "=== 管理命令 ==="
echo "查看任务状态: launchctl list | grep com.etf-tool.wind-download"
echo "手动执行任务: launchctl start com.etf-tool.wind-download"
echo "卸载任务: launchctl unload $PLIST_TARGET"
echo "查看日志: tail -f $LOG_DIR/wind_download_out.log"
echo ""
echo "✅ 安装完成！明天早上8点将自动开始下载Wind数据。"
