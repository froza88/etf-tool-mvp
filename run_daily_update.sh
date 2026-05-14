#!/bin/bash
# ETF数据自动更新 - 定时任务启动脚本
# 每天凌晨2点自动运行

cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp
/usr/bin/python3 auto_update_etf_data.py >> logs/etf_update.log 2>&1

# 记录完成时间
echo "✅ 更新完成: $(date)" >> logs/etf_update.log
