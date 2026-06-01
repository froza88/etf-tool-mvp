#! /bin/bash
# 用macOS Safari的WebKit将SVG渲染为PNG
# 需要：Safari浏览器（已安装）

SVG_PATH="$HOME/WorkBuddy/Claw/etf-tool-mvp/articles/沪深300ETF全面对比_20260531/cover_沪深300ETF全面对比.svg"
OUTPUT_PATH="$HOME/Desktop/cover_沪深300ETF全面对比.png"

echo "在Safari中打开封面..."
open -a Safari "$SVG_PATH"

echo ""
echo "=== 请手动导出PNG ==="
echo "1. Safari打开图片后，点击图片"
echo "2. 按 Cmd+S 或 右键 → 另存为图片"
echo "3. 保存到桌面"
echo ""
echo "或者用更简单的方法："
echo "打开预览后直接截图：Cmd+Shift+4 → 空格键 → 点击窗口"
