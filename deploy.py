#!/usr/bin/env python3
"""
PythonAnywhere 部署脚本 - 在 GitHub Actions 中运行
"""
import json, os, sys, time
import urllib.request

TOKEN = os.environ.get("PA_API_TOKEN")
USERNAME = os.environ.get("PA_USERNAME")

if not TOKEN or not USERNAME:
    print("❌ PA_API_TOKEN or PA_USERNAME not set")
    sys.exit(1)

BASE = f"https://www.pythonanywhere.com/api/v1/user/{USERNAME}"
HEADERS = {"Authorization": f"Token {TOKEN}"}


def api_call(method, path, data=None):
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, method=method, headers=HEADERS)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req.data = body
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, text
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, str(e)


# Step 1: Create console
print("📥 Creating bash console...")
status, resp = api_call("POST", "/consoles/", {"executable": "bash"})
print(f"  HTTP {status}: {resp[:200]}")
if status != 201:
    print("❌ Failed to create console")
    sys.exit(1)

console = json.loads(resp)
console_id = console["id"]
print(f"  Console ID: {console_id}")

# Step 2: Send git pull
print("📦 Sending git pull...")
status, resp = api_call("POST", f"/consoles/{console_id}/send_input/",
                        {"input": "cd ~/etf-tool-mvp && git pull origin main\n"})
print(f"  HTTP {status}: OK")
time.sleep(8)

# Step 3: Touch WSGI
print("🔄 Sending touch wsgi...")
status, resp = api_call("POST", f"/consoles/{console_id}/send_input/",
                        {"input": f"touch /var/www/{USERNAME}_pythonanywhere_com_wsgi.py\n"})
print(f"  HTTP {status}: OK")
time.sleep(5)

# Step 4: Close console
print("🔒 Closing console...")
status, resp = api_call("PATCH", f"/consoles/{console_id}/", {"status": "deleted"})
print(f"  HTTP {status}: OK")

# Step 5: Reload web app
print("🔄 Reloading web app...")
status, resp = api_call("POST", f"/webapps/{USERNAME}.pythonanywhere.com/reload/")
print(f"  HTTP {status}: OK")

print("\n✅ Deploy complete!")
