#!/usr/bin/env python3
"""
PythonAnywhere 部署脚本 - v4
使用 Schedule API 创建一次性 git pull 任务，然后 Reload
如果 Schedule 不可用，回退为仅 Reload
"""
import json, os, sys, time
from datetime import datetime, timedelta
import urllib.request

TOKEN = os.environ.get("PA_API_TOKEN")
USERNAME = os.environ.get("PA_USERNAME")
if not TOKEN or not USERNAME:
    print("❌ Missing PA_API_TOKEN or PA_USERNAME")
    sys.exit(1)

B0 = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}"
H = {"Authorization": f"Token {TOKEN}"}

def api(method, path, data=None):
    url = f"{B0}{path}"
    req = urllib.request.Request(url, method=method, headers=H)
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)

# Step 1: Schedule one-time git pull task
print("📦 Scheduling git pull...")
n = datetime.utcnow() + timedelta(minutes=1)
task = {
    "command": f"cd ~/{USERNAME}/etf-tool-mvp && git pull origin main && touch /var/www/{USERNAME}_pythonanywhere_com_wsgi.py",
    "interval": "once", "hour": n.hour, "minute": n.minute,
    "description": "gh-deploy"
}
s, r = api("POST", "/schedule/", task)
print(f"  Schedule: HTTP {s}")

if s == 201:
    print(f"  Task set for {n.hour:02d}:{n.minute:02d} UTC, waiting...")
    time.sleep(75)

# Step 2: Reload
print("🔄 Reloading...")
s, r = api("POST", f"/webapps/{USERNAME}.pythonanywhere.com/reload/")
print(f"  Reload: HTTP {s}")

# Step 3: Cleanup schedule
gs, gr = api("GET", "/schedule/")
if gs == 200:
    for t in json.loads(gr):
        if t.get("description") == "gh-deploy":
            api("DELETE", f"/schedule/{t['id']}/")

print("\n✅ Done!" if s == 200 else "\n❌ Failed")
sys.exit(0 if s == 200 else 1)
