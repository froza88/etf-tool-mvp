#!/usr/bin/env python3
"""
PythonAnywhere 部署脚本
先用 Console API 执行 git pull + touch wsgi，然后 Reload
如果 Console 创建失败，回退为仅 Reload（依赖已有代码）
"""
import json, os, sys, time
import urllib.request

TOKEN = os.environ.get("PA_API_TOKEN")
USERNAME = os.environ.get("PA_USERNAME")

if not TOKEN or not USERNAME:
    print("❌ PA_API_TOKEN or PA_USERNAME not set")
    sys.exit(1)

BASE_V0 = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}"
BASE_V1 = f"https://www.pythonanywhere.com/api/v1/user/{USERNAME}"
HEADERS = {"Authorization": f"Token {TOKEN}"}
HAS_CONSOLE = False

def api(base, method, path, data=None):
    url = f"{base}{path}"
    req = urllib.request.Request(url, method=method, headers=HEADERS)
    if data is not None:
        req.data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as e:
        return 0, str(e)

# ===== Step 1: 创建控制台 (v0 API) =====
print("📥 Creating bash console...")
s, r = api(BASE_V0, "POST", "/consoles/", {"executable": "bash", "working_directory": f"/home/{USERNAME}/etf-tool-mvp"})
print(f"  HTTP {s}: {r[:300]}")
if s == 201:
    console = json.loads(r)
    cid = console["id"]
    print(f"  Console ID: {cid}")
    HAS_CONSOLE = True

    # Step 2: git pull
    print("📦 git pull...")
    api(BASE_V0, "POST", f"/consoles/{cid}/send_input/",
        {"input": "cd ~/etf-tool-mvp && git pull origin main\n"})
    time.sleep(8)

    # Step 3: touch wsgi
    print("🔄 touch wsgi...")
    api(BASE_V0, "POST", f"/consoles/{cid}/send_input/",
        {"input": f"touch /var/www/{USERNAME}_pythonanywhere_com_wsgi.py\n"})
    time.sleep(3)

    # Step 4: 关闭控制台 (v0 uses DELETE not PATCH)
    print("🔒 Closing console...")
    api(BASE_V0, "DELETE", f"/consoles/{cid}/")
    print("  Console closed")
else:
    print("⚠️  Console creation failed, will do reload only (code may be stale)")

# ===== Step 5: Reload web app (v0 API) =====
print("🔄 Reloading web app...")
s, r = api(BASE_V0, "POST", f"/webapps/{USERNAME}.pythonanywhere.com/reload/")
print(f"  HTTP {s}: {r[:200]}")

if s == 200:
    print("\n✅ Deploy complete!")
else:
    print("\n❌ Reload failed!")
    sys.exit(1)
