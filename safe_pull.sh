#!/bin/bash
# safe_pull.sh - 安全拉取脚本 (防回滚)
# 功能：在 git pull 前检查数据版本，防止新数据被旧数据覆盖
# 使用方式：./safe_pull.sh [--force]

set -e

# 配置
DATA_FILE="etf_standard_data.json"
VERSION_FILE="data_version.json"
REMOTE=${1:-"origin/main"}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否强制拉取
if [[ "$1" == "--force" ]] || [[ "$2" == "--force" ]]; then
    log_warn "强制拉取模式，跳过版本检查"
    git pull $REMOTE
    exit $?
fi

# 1. 检查本地是否有 data_version.json
if [[ ! -f "$VERSION_FILE" ]]; then
    log_warn "本地无 $VERSION_FILE，执行正常 pull"
    git pull $REMOTE
    exit $?
fi

# 2. 读取本地版本
LOCAL_VERSION=$(python3 -c "import json; print(json.load(open('$VERSION_FILE'))['version'])" 2>/dev/null || echo "")
if [[ -z "$LOCAL_VERSION" ]]; then
    log_error "无法读取本地版本信息"
    exit 1
fi

log_info "本地版本: $LOCAL_VERSION"

# 3. 读取远程版本
REMOTE_VERSION=$(git show $REMOTE:$VERSION_FILE 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin)['version'])" 2>/dev/null || echo "")
if [[ -z "$REMOTE_VERSION" ]]; then
    log_warn "远程无 $VERSION_FILE，执行正常 pull"
    git pull $REMOTE
    exit $?
fi

log_info "远程版本: $REMOTE_VERSION"

# 4. 比较版本 (简单字符串比较，ISO 8601 格式可直接比较)
if [[ "$LOCAL_VERSION" > "$REMOTE_VERSION" ]]; then
    # 本地更新
    log_warn "⚠️  本地数据 ($LOCAL_VERSION) 比远程 ($REMOTE_VERSION) 更新！"
    log_warn "如果直接 pull，本地新数据将被覆盖！"
    echo ""
    echo "请选择操作:"
    echo "  1) 先 push 本地数据，再 pull (推荐)"
    echo "  2) 强制 pull (会丢失本地数据)"
    echo "  3) 取消操作"
    echo ""
    read -p "请输入选择 [1/2/3]: " choice
    
    case $choice in
        1)
            log_info "先 push 本地数据..."
            git add $DATA_FILE $VERSION_FILE
            git commit -m "data: auto-sync before pull (local newer)"
            git push $REMOTE
            
            log_info "Push 完成，现在 pull..."
            git pull $REMOTE
            ;;
        2)
            log_warn "强制 pull，本地数据将丢失！"
            git pull $REMOTE
            ;;
        3)
            log_info "取消操作"
            exit 0
            ;;
        *)
            log_error "无效选择"
            exit 1
            ;;
    esac
else
    # 远程更新或相同
    log_info "远程数据更新或相同，执行 pull"
    git pull $REMOTE
fi

log_info "✅ Pull 完成"
