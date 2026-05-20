#!/bin/bash
# sync_data.sh - 三地数据同步脚本
# 功能：将本地数据同步到 GitHub 和 PythonAnywhere
# 优先级：本地 → GitHub → PythonAnywhere
# 同步窗口：不超过 10 分钟

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DATA_FILE="etf_standard_data.json"
VERSION_FILE="data_version.json"
LOG_FILE="sync_log_$(date +%Y%m%d).log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查 Git 状态
check_git_status() {
    log "检查 Git 状态..."
    if ! git diff --quiet "$DATA_FILE" "$VERSION_FILE"; then
        log "检测到数据变更，准备提交"
        return 0
    else
        log "数据无变更，跳过提交"
        return 1
    fi
}

# 更新版本信息
update_version() {
    log "更新版本信息..."
    python3 update_data_version.py --source local
}

# 提交到 Git
commit_and_push() {
    log "提交到 Git..."
    git add "$DATA_FILE" "$VERSION_FILE"
    git commit -m "data: auto-sync $(date +%Y-%m-%d_%H:%M:%S)"
    
    log "推送到 GitHub..."
    git push origin main
    
    log "✅ Git 同步完成"
}

# 触发 PythonAnywhere 同步
trigger_pa_sync() {
    log "触发 PythonAnywhere 同步..."
    
    # 方式1: 通过 API (如果已实现)
    # curl -X POST https://froza.pythonanywhere.com/api/sync
    
    # 方式2: 通过 GitHub Webhook (推荐)
    # GitHub Webhook 会自动触发 PythonAnywhere 的 pull
    
    # 方式3: 手动提醒 (当前方案)
    log "⚠️  请手动在 PythonAnywhere 执行: git pull origin main"
    log "   或在 PythonAnywhere 配置 webhook/cron 自动拉取"
}

# 验证同步状态
verify_sync() {
    log "验证同步状态..."
    
    # 检查本地版本
    LOCAL_VERSION=$(python3 -c "import json; print(json.load(open('$VERSION_FILE'))['version'])")
    log "本地版本: $LOCAL_VERSION"
    
    # 检查远程版本 (通过 Git)
    git fetch origin main
    REMOTE_VERSION=$(git show origin/main:$VERSION_FILE | python3 -c "import sys, json; print(json.load(sys.stdin)['version'])")
    log "远程版本: $REMOTE_VERSION"
    
    # 比较时间差
    LOCAL_TIME=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${LOCAL_VERSION%+08:00}" +%s 2>/dev/null || echo "0")
    REMOTE_TIME=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${REMOTE_VERSION%+08:00}" +%s 2>/dev/null || echo "0")
    TIME_DIFF=$((LOCAL_TIME - REMOTE_TIME))
    
    if [ $TIME_DIFF -gt 600 ]; then
        log "⚠️  警告: 本地比远程新 ${TIME_DIFF} 秒 (>10分钟)"
    else
        log "✅ 时间差在正常范围内: ${TIME_DIFF} 秒"
    fi
}

# 主流程
main() {
    log "========== 开始三地数据同步 =========="
    
    # 1. 更新版本信息
    update_version
    
    # 2. 检查是否需要提交
    if check_git_status; then
        # 3. 提交并推送
        commit_and_push
        
        # 4. 触发 PythonAnywhere 同步
        trigger_pa_sync
        
        # 5. 验证同步状态
        verify_sync
    else
        log "无需同步"
    fi
    
    log "========== 同步完成 =========="
}

# 执行
main "$@"
