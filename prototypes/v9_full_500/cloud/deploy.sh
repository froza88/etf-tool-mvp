#!/bin/bash
# ETF 对比工具 · COS + SCF 一键部署
# 用法：bash deploy.sh <COS_BUCKET> <COS_REGION>

set -e
BUCKET="${1:?请提供 COS 桶名，如：etf-compare-1234567890}"
REGION="${2:-ap-guangzhou}"
STATIC_DIR="../"
CLOUD_DIR="$(dirname "$0")"

echo "=== 1/3 上传静态文件到 COS ==="
# HTML + JS + JSON（无需 Python 后端）
for f in comparison_ca_hybrid.html etf_data_embed.js etf_core_data.json; do
  echo "  上传 $f ..."
  coscmd -b "$BUCKET" -r "$REGION" upload "../$f" "/$f" 2>/dev/null || \
  echo "  ⚠️ coscmd 未配置，请手动上传 $f"
done

echo ""
echo "=== 2/3 部署 SCF 云函数 ==="
echo "  请到腾讯云控制台操作："
echo "  1. 云函数 SCF → 新建 → Python 3.9"
echo "  2. 上传 enrich_scf.py 作为函数代码"
echo "  3. 执行方法：enrich_scf.main_handler"
echo "  4. 内存 128MB，超时 15 秒"
echo "  5. 触发器 → API 网关触发器 → 路径 /api/ttjj + /api/health"
echo ""

echo "=== 3/3 配置 HTML 中的 API 地址 ==="
echo "  SCF 部署完成后，会得到 API 网关 URL，格式类似："
echo "  https://service-xxx.gz.apigw.tencentcs.com/release/api/ttjj"
echo "  然后修改 comparison_ca_hybrid.html 中的 REALTIME_API 变量"
echo ""

echo "=== 完成！静态页面访问地址 ==="
echo "  https://${BUCKET}.cos.${REGION}.myqcloud.com/comparison_ca_hybrid.html"
echo ""
echo "或 CDN 加速后：自定义域名绑定 COS 桶即可"
