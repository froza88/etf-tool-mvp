#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量上传 ETF 历史K线到腾讯云 COS

用法：
  # 设置环境变量（或从 .env 文件读取）
  export TENCENT_SECRET_ID="你的SecretId"
  export TENCENT_SECRET_KEY="你的SecretKey"
  export COS_BUCKET="etf-history-1437728630"
  export COS_REGION="ap-beijing"

  # 上传（增量，只上传有变化的文件）
  python3 cos_upload.py

  # 强制重新上传所有文件
  python3 cos_upload.py --force

  # 只上传指定 ETF（调试用）
  python3 cos_upload.py --codes 510300,510500,159915

依赖：
  pip install cos-python-sdk-v5 python-dotenv
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime

# 尝试从 .env 文件加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 腾讯云 COS SDK
try:
    from qcloud_cos import CosConfig, CosS3Client
except ImportError:
    print("❌ 请先安装依赖: pip install cos-python-sdk-v5")
    sys.exit(1)

# ── 配置（从环境变量读取）──────────────────────────────────────────────
SECRET_ID = os.environ.get("TENCENT_SECRET_ID", "")
SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY", "")
BUCKET = os.environ.get("COS_BUCKET", "etf-history-1437728630")
REGION = os.environ.get("COS_REGION", "ap-beijing")  # 北京地域

# 本地数据目录
ROOT = Path(__file__).parent
HISTORY_DIR = ROOT / "data" / "history"

# COS 路径前缀（可选，如 "history/"）
COS_PREFIX = "history/"

# ── 工具函数 ──────────────────────────────────────────────────────────

def get_cos_client():
    """创建 COS 客户端"""
    if not SECRET_ID or not SECRET_KEY:
        print("❌ 缺少环境变量:")
        print("   TENCENT_SECRET_ID  你的 SecretId")
        print("   TENCENT_SECRET_KEY 你的 SecretKey")
        print("")
        print("设置方式（Linux/macOS）:")
        print("  export TENCENT_SECRET_ID='AKID...'")
        print("  export TENCENT_SECRET_KEY='xxxxxx'")
        print("")
        print("或从 .env 文件加载（需安装 python-dotenv）")
        sys.exit(1)

    config = CosConfig(
        Region=REGION,
        SecretId=SECRET_ID,
        SecretKey=SECRET_KEY,
        Scheme="https",
    )
    return CosS3Client(config)


def compute_etag(local_path):
    """计算本地文件的 ETag（COS 用 MD5）"""
    md5 = hashlib.md5()
    with open(local_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return f'"{md5.hexdigest()}"'  # COS ETag 带引号


def cos_object_exists(client, key, local_etag):
    """检查 COS 上是否已有相同文件（通过 ETag 判断）"""
    try:
        head = client.head_object(Bucket=BUCKET, Key=key)
        cos_etag = head.get("ETag", "")
        return cos_etag == local_etag
    except Exception:
        return False


def upload_one(client, local_path, cos_key):
    """上传单个文件到 COS"""
    try:
        with open(local_path, "rb") as f:
            client.put_object(
                Bucket=BUCKET,
                Body=f,
                Key=cos_key,
                StorageClass="STANDARD",  # 标准存储
            )
        return True, None
    except Exception as e:
        return False, str(e)


# ── 主流程 ─────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="上传 ETF 历史K线到腾讯云 COS")
    parser.add_argument("--force", action="store_true", help="强制重新上传所有文件")
    parser.add_argument("--codes", type=str, default="", help="只上传指定ETF代码，逗号分隔")
    parser.add_argument("--prefix", type=str, default=COS_PREFIX, help=f"COS路径前缀（默认: {COS_PREFIX}）")
    parser.add_argument("--dry-run", action="store_true", help="只展示，不实际上传")
    args = parser.parse_args()

    # 检查本地数据目录
    if not HISTORY_DIR.exists():
        print(f"❌ 本地数据目录不存在: {HISTORY_DIR}")
        print("   请先运行: python3 batch_fill_history.py --all")
        sys.exit(1)

    # 确定要上传的文件列表
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",")]
        files = [(HISTORY_DIR / f"{c}.json") for c in codes]
        files = [f for f in files if f.exists()]
        if not files:
            print(f"❌ 指定的 ETF 文件不存在: {args.codes}")
            sys.exit(1)
    else:
        files = sorted(HISTORY_DIR.glob("*.json"))
        if not files:
            print(f"❌ {HISTORY_DIR} 中没有 .json 文件")
            sys.exit(1)

    total = len(files)
    print(f"📦 待上传: {total} 个文件")
    print(f"🪣  Bucket: {BUCKET} ({REGION})")
    print(f"📁  路径前缀: {args.prefix}")
    if args.force:
        print(f"🔄 强制模式: 重新上传所有文件")
    if args.dry_run:
        print(f"🏃  Dry-run 模式: 不实际上传")
    print()

    if args.dry_run:
        for f in files[:10]:
            print(f"  [DRY] {f.name} ({f.stat().st_size // 1024} KB)")
        if total > 10:
            print(f"  ... 还有 {total - 10} 个")
        return

    # 创建 COS 客户端
    client = get_cos_client()
    print(f"✅ COS 客户端已创建\n")

    # 开始上传
    ok = skip = fail = 0
    start_time = time.time()

    for i, local_path in enumerate(files, 1):
        cos_key = f"{args.prefix}{local_path.name}"
        etag = compute_etag(local_path)

        # 增量检查（非 force 模式）
        if not args.force and cos_object_exists(client, cos_key, etag):
            skip += 1
            if i % 50 == 0:
                print(f"  [{i:4d}/{total}] {local_path.name} ⏭  已存在（跳过）")
            continue

        # 上传
        success, error = upload_one(client, local_path, cos_key)
        if success:
            ok += 1
            if i % 20 == 0 or i == total:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remain = (total - i) / rate if rate > 0 else 0
                print(f"  [{i:4d}/{total}] {local_path.name} ✅  ({elapsed:.0f}s, 剩余~{remain:.0f}s)")
        else:
            fail += 1
            print(f"  [{i:4d}/{total}] {local_path.name} ❌ {error[:60]}")

    # 报告
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"上传完成!")
    print(f"  ✅ 成功: {ok} 个")
    print(f"  ⏭  跳过: {skip} 个（已存在）")
    print(f"  ❌ 失败: {fail} 个")
    print(f"  ⏱️  耗时: {elapsed:.1f} 秒")
    print(f"  🔗  CDN 地址: https://{BUCKET}.cos.{REGION}.myqcloud.com/{args.prefix}")
    print(f"{'='*60}")

    if ok > 0:
        print(f"\n💡 前端访问示例:")
        print(f"   fetch('https://{BUCKET}.cos.{REGION}.myqcloud.com/{args.prefix}510300.json')")


if __name__ == "__main__":
    main()
