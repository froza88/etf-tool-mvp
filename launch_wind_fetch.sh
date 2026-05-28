#!/bin/bash
# launcher.sh - 启动Python脚本，让它成为孤儿进程（避免SIGHUP）
cd "$(dirname "$0")"

# 启动Python脚本
python3 wind_fetch_v3.py > wind_v3.log 2>&1 &
PID=$!

# 从job table移除（避免SIGHUP）
disown $PID

echo "Launched Wind fetch (PID: $PID)"
echo "Log: wind_v3.log"
