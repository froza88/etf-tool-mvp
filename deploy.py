#!/usr/bin/env python3
"""
PythonAnywhere 部署脚本
只做 Reload（git pull 由 PA 定时任务每小时自动执行）
"""
import os, sys, json, urllib.request

TOKEN = os.environ.get("PA_API_TOKEN")
USERNAME = os.environ.get("PA_USERNAME")
if not TOKEN or not USERNAME:
    print("❌ Missing PA_API_TOKEN or PA_USERNAME")
    sys.exit(1)

url = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}/webapps/{USERNAME}.pythonanywhere.com/reload/"
req = urllib.request.Request(url, method="POST",
    headers={"Authorization": f"Token {TOKEN}"})

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"✅ Reload: HTTP {resp.status}")
        sys.exit(0)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"❌ Reload failed: HTTP {e.code} {body[:200]}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
