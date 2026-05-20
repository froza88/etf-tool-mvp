#!/bin/bash
# 本地一键部署脚本 - 自动化本地提交推送 + 提示PA部署
# 用法: bash deploy.sh "commit message"
# 或: ./deploy.sh "commit message"

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否在正确的目录
check_directory() {
    if [ ! -f "app.py" ] || [ ! -d ".git" ]; then
        log_error "请在 etf-tool-mvp 项目根目录运行此脚本"
        exit 1
    fi
}

# 检查git状态
check_git_status() {
    log_info "检查git状态..."
    
    # 检查是否有未提交的更改
    if [ -z "$(git status --porcelain)" ]; then
        log_warn "没有未提交的更改，无需部署"
        echo ""
        read -p "是否强制重新部署？(y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
    
    # 检查是否在main分支
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        log_error "当前不在main分支 (当前: $CURRENT_BRANCH)"
        exit 1
    fi
    
    log_success "git状态检查通过"
}

# 本地提交并推送
commit_and_push() {
    local commit_msg="$1"
    
    if [ -z "$commit_msg" ]; then
        log_error "请提供commit消息"
        echo "用法: bash deploy.sh \"commit message\""
        exit 1
    fi
    
    log_info "开始本地提交..."
    
    # Git add
    log_info "[1/3] Git add..."
    git add .
    log_success "已添加所有更改"
    
    # Git commit
    log_info "[2/3] Git commit..."
    git commit -m "$commit_msg" || {
        log_warn "git commit失败（可能无更改）"
    }
    
    # Git push
    log_info "[3/3] Git push到GitHub..."
    git push origin main || {
        log_error "git push失败"
        log_info "可能的原因："
        log_info "  1. 网络连接问题"
        log_info "  2. GitHub认证失败（需重新登录）"
        log_info "  3. 远程有新的提交（需先pull）"
        exit 1
    }
    
    log_success "已推送到GitHub"
}

# 打开PA Console并复制命令
open_pa_console() {
    log_info "准备PA部署..."
    
    # 部署命令
    DEPLOY_CMD="cd ~/etf-tool-mvp && bash pa_deploy.sh"
    
    # 复制到剪贴板（macOS）
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "$DEPLOY_CMD" | pbcopy
        log_success "部署命令已复制到剪贴板"
    fi
    
    # 打开PA Console页面
    log_info "正在打开PA Console页面..."
    open "https://www.pythonanywhere.com/consoles/"
    
    echo ""
    echo "=========================================="
    echo "📋 下一步：在PA Console中部署"
    echo "=========================================="
    echo ""
    echo "1. 在打开的PA Console页面中，点击 'Bash' 控制台"
    echo "2. 粘贴以下命令（已复制到剪贴板）："
    echo "   ${YELLOW}${DEPLOY_CMD}${NC}"
    echo "3. 按回车执行"
    echo "4. 等待部署完成（看到 '部署完成' 提示）"
    echo ""
    echo "=========================================="
    echo ""
}

# 验证部署
verify_deployment() {
    log_info "验证PA部署..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        # 获取PA版本
        PA_VERSION=$(curl -s "https://froza.pythonanywhere.com/api/version" 2>/dev/null || echo "ERROR")
        
        if [ "$PA_VERSION" != "ERROR" ] && [ -n "$PA_VERSION" ]; then
            # 获取本地版本
            LOCAL_VERSION=$(git rev-parse HEAD)
            
            if [ "$PA_VERSION" = "$LOCAL_VERSION" ]; then
                log_success "部署验证成功！PA版本与本地一致"
                log_info "PA版本: $PA_VERSION"
                return 0
            else
                log_warn "尝试 $attempt/$max_attempts: PA版本($PA_VERSION)与本地($LOCAL_VERSION)不一致"
            fi
        else
            log_warn "尝试 $attempt/$max_attempts: 无法获取PA版本"
        fi
        
        sleep 2
    done
    
    log_error "部署验证超时！PA可能未成功部署"
    log_info "请手动检查："
    log_info "  curl https://froza.pythonanywhere.com/api/version"
    return 1
}

# 主函数
main() {
    echo "=========================================="
    echo "🚀 ETF工具本地一键部署"
    echo "=========================================="
    echo ""
    
    # 检查目录
    check_directory
    
    # 检查git状态
    check_git_status
    
    # 本地提交并推送
    commit_and_push "$1"
    
    # 打开PA Console
    open_pa_console
    
    # 等待用户确认
    echo "部署完成后，按 Enter 继续验证..."
    read
    
    # 验证部署
    verify_deployment
    
    echo ""
    echo "=========================================="
    echo "🎉 部署流程完成！"
    echo "=========================================="
    echo ""
    echo "验证链接："
    echo "  - 首页: https://froza.pythonanywhere.com/"
    echo "  - API版本: https://froza.pythonanywhere.com/api/version"
    echo ""
}

# 运行主函数
main "$@"
