#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[信息]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[步骤]${NC} $1"
}

print_url() {
    echo -e "${CYAN}[访问地址]${NC} $1"
}

# 错误处理函数
handle_error() {
    print_error "$1 失败，退出代码: $2"
    exit $2
}

# 显示启动横幅
show_banner() {
    echo -e "${GREEN}"
    echo "****************************************************"
    echo "*                                                  *"
    echo "*             HAnime 服务器启动系统                *"
    echo "*                                                  *"
    echo "****************************************************"
    echo -e "${NC}"
    echo -e "${CYAN}版本: 1.0.0${NC}"
    echo -e "${CYAN}启动时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo ""
}

# 启动 Nginx
start_nginx() {
    print_step "启动 Nginx 服务..."
    if service nginx start; then
        print_info "✓ Nginx 服务启动成功"
        # 获取主机IP地址
        if command -v hostname &> /dev/null; then
            HOST_IP=$(hostname -I 2>/dev/null || hostname -i | awk '{print $1}')
            echo -e "\n${CYAN}访问地址:${NC}"
            echo -e "  ${BOLD}本地访问:${NC} http://localhost:7788"
            echo -e "  ${BOLD}局域网访问:${NC} http://${HOST_IP}:7788"
            echo ""
        fi
    else
        handle_error "Nginx 启动" $?
    fi
}

# 启动后端应用
start_backend() {
    print_step "启动后端服务..."
    cd /app/backend || handle_error "切换到后端目录" $?
    
    print_info "正在初始化后端服务..."
    echo -e "  ${BOLD}工作目录:${NC} $(pwd)"
    echo -e "  ${BOLD}Python版本:${NC} $(python3 --version)"
    echo ""
    
    python3 main.py || handle_error "启动 Python 后端" $?
}

# 主函数
main() {
    show_banner
    start_nginx
    start_backend
    
    # 这行代码通常不会执行到，因为 python3 main.py 会阻塞
    # 如果执行到这里，说明所有进程都已经退出
    print_error "所有服务已意外停止。请检查日志获取更多信息。"
}

# 执行主函数
main 