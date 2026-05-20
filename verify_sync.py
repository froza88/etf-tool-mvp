#!/usr/bin/env python3
"""
verify_sync.py - 验证三地数据同步一致性

功能：
1. 检查本地数据版本
2. 检查 GitHub 数据版本 (通过 git)
3. 检查 PythonAnywhere 数据版本 (通过 API 或假设)
4. 对比时间戳，报告不一致
5. 检查时间差是否超过 10 分钟

使用方式：
    python3 verify_sync.py [--fix]
"""

import json
import subprocess
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

def parse_iso_time(time_str):
    """解析 ISO 8601 时间字符串"""
    # 移除时区信息简化处理
    time_str = time_str.replace('+08:00', '').replace('Z', '')
    return datetime.fromisoformat(time_str)

def get_local_version(version_file='data_version.json'):
    """获取本地版本信息"""
    if not Path(version_file).exists():
        return None
    
    with open(version_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_github_version(repo='origin/main', version_file='data_version.json'):
    """获取 GitHub 版本信息 (通过 git)"""
    try:
        result = subprocess.run(
            ['git', 'show', f'{repo}:{version_file}'],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        return None

def get_pa_version(api_url='https://froza.pythonanywhere.com/api/version'):
    """获取 PythonAnywhere 版本信息 (通过 API)"""
    try:
        import urllib.request
        with urllib.request.urlopen(api_url, timeout=5) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"⚠️  无法获取 PythonAnywhere 版本: {e}")
        return None

def check_time_diff(local_time, remote_time, max_diff_seconds=600):
    """检查时间差是否在允许范围内 (默认 10 分钟 = 600 秒)"""
    if not local_time or not remote_time:
        return None
    
    local_dt = parse_iso_time(local_time)
    remote_dt = parse_iso_time(remote_time)
    
    diff_seconds = abs((local_dt - remote_dt).total_seconds())
    is_ok = diff_seconds <= max_diff_seconds
    
    return {
        'diff_seconds': diff_seconds,
        'diff_minutes': round(diff_seconds / 60, 1),
        'is_ok': is_ok,
        'max_diff_minutes': max_diff_seconds / 60
    }

def verify_consistency():
    """验证三地数据一致性"""
    print("=" * 60)
    print("三地数据同步一致性验证")
    print("=" * 60)
    
    # 1. 获取三地版本信息
    local_ver = get_local_version()
    github_ver = get_github_version()
    pa_ver = get_pa_version()
    
    versions = {
        'local': local_ver,
        'github': github_ver,
        'pythonanywhere': pa_ver
    }
    
    # 2. 打印版本信息
    print("\n📊 版本信息:")
    print("-" * 60)
    
    for location, ver in versions.items():
        if ver:
            print(f"{location:15} | Version: {ver['version']}")
            print(f"{'':15} | Source: {ver['source']}")
            print(f"{'':15} | ETF Count: {ver['etf_count']}")
            print(f"{'':15} | Checksum: {ver['checksum'][:16]}...")
            print(f"{'':15} | Coverage: {ver['fields_coverage']}")
        else:
            print(f"{location:15} | ❌ 无法获取版本信息")
        print()
    
    # 3. 检查时间差
    print("\n⏱️  时间差检查 (允许最大: 10 分钟):")
    print("-" * 60)
    
    time_checks = []
    
    if local_ver and github_ver:
        check = check_time_diff(local_ver['version'], github_ver['version'])
        time_checks.append(('Local ↔ GitHub', check))
    
    if local_ver and pa_ver:
        check = check_time_diff(local_ver['version'], pa_ver['version'])
        time_checks.append(('Local ↔ PythonAnywhere', check))
    
    if github_ver and pa_ver:
        check = check_time_diff(github_ver['version'], pa_ver['version'])
        time_checks.append(('GitHub ↔ PythonAnywhere', check))
    
    for pair, check in time_checks:
        if check:
            status = "✅" if check['is_ok'] else "❌"
            print(f"{pair:25} | {status} {check['diff_minutes']} 分钟 (最大 {check['max_diff_minutes']} 分钟)")
        else:
            print(f"{pair:25} | ⚠️  无法检查")
    
    # 4. 检查数据一致性 (checksum)
    print("\n🔍 数据一致性检查 (Checksum):")
    print("-" * 60)
    
    if local_ver and github_ver:
        match = local_ver['checksum'] == github_ver['checksum']
        status = "✅" if match else "❌"
        print(f"{'Local ↔ GitHub':25} | {status} {'一致' if match else '不一致'}")
    
    if local_ver and pa_ver:
        match = local_ver['checksum'] == pa_ver['checksum']
        status = "✅" if match else "❌"
        print(f"{'Local ↔ PythonAnywhere':25} | {status} {'一致' if match else '不一致'}")
    
    # 5. 总结
    print("\n" + "=" * 60)
    print("总结:")
    print("=" * 60)
    
    issues = []
    
    # 检查时间差问题
    for pair, check in time_checks:
        if check and not check['is_ok']:
            issues.append(f"⏱️  {pair} 时间差 {check['diff_minutes']} 分钟 > 10 分钟")
    
    # 检查数据一致性问题
    if local_ver and github_ver and local_ver['checksum'] != github_ver['checksum']:
        issues.append("🔍 Local 和 GitHub 数据不一致")
    
    if local_ver and pa_ver and local_ver['checksum'] != pa_ver['checksum']:
        issues.append("🔍 Local 和 PythonAnywhere 数据不一致")
    
    if issues:
        print("❌ 发现问题:")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("✅ 三地数据同步正常")
        return True

def main():
    parser = argparse.ArgumentParser(description='验证三地数据同步一致性')
    parser.add_argument('--fix', action='store_true', help='自动修复不一致问题')
    
    args = parser.parse_args()
    
    success = verify_consistency()
    
    if not success and args.fix:
        print("\n🔧 尝试自动修复...")
        # TODO: 实现自动修复逻辑
        print("⚠️  自动修复功能尚未实现")
    
    return 0 if success else 1

if __name__ == '__main__':
    exit(main())
