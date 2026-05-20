#!/usr/bin/env python3
"""
测试单元4：update_data_version.py 功能测试

测试目标：
  测试 update_data_version.py 对三个来源（local/github/pythonanywhere）都能正确更新

测试类型：
  🤖 自动化测试（可重复运行）

运行方式：
  cd /Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/
  python3 task_packages/sync_test_units/test_04_update_data_version.py
"""

import subprocess
import sys
import json
import os

def run_update_version(source):
    """运行 update_data_version.py --source <source>"""
    result = subprocess.run(
        [sys.executable, "update_data_version.py", "--source", source],
        capture_output=True, text=True,
        cwd="/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp"
    )
    return result.returncode == 0, result.stdout, result.stderr

def check_data_version(source):
    """检查 data_version.json 的内容是否正确"""
    try:
        with open("/Users/apangduo/WorkBuddy/Claw/etf-tool-mvp/data_version.json", "r") as f:
            data = json.load(f)
        if data.get("source") != source:
            return False, f"source期望'{source}'，实际'{data.get('source')}'"
        if "version" not in data:
            return False, "缺少version字段"
        if "checksum" not in data:
            return False, "缺少checksum字段"
        return True, "OK"
    except Exception as e:
        return False, str(e)

def test_source(source):
    """测试单个来源"""
    print(f"\n--- 测试来源: {source} ---")
    
    # 运行 update_data_version.py
    success, stdout, stderr = run_update_version(source)
    if not success:
        print(f"❌ 运行失败: {stderr}")
        return False
    
    # 检查结果
    ok, msg = check_data_version(source)
    if ok:
        print(f"✅ 来源 {source} 测试通过")
        return True
    else:
        print(f"❌ 来源 {source} 测试失败: {msg}")
        return False

def main():
    print("=" * 60)
    print("测试单元4：update_data_version.py 功能测试")
    print("=" * 60)
    
    results = {}
    for source in ["local", "github", "pythonanywhere"]:
        results[source] = test_source(source)
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试单元4 报告")
    print("=" * 60)
    for source, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"  {status} {source}")
    
    all_pass = all(results.values())
    if all_pass:
        print("\n✅ 所有测试通过")
    else:
        print("\n❌ 部分测试失败")
    
    sys.exit(0 if all_pass else 1)

if __name__ == "__main__":
    main()
