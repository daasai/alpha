#!/bin/bash

# DAAS Alpha 服务管理脚本
# 功能：启动、停止、重启和查询运行状态

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# PID 文件目录
PID_DIR="$PROJECT_DIR/.pids"
mkdir -p "$PID_DIR"

# PID 文件路径
API_PID_FILE="$PID_DIR/api.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

# 日志文件目录
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# API 配置
API_HOST="127.0.0.1"
API_PORT=8000
API_LOG="$LOG_DIR/api.log"

# 前端配置
FRONTEND_DIR="$PROJECT_DIR/frontend"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# 检查进程是否运行
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# 检查端口是否被占用
is_port_in_use() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# 打印状态信息
print_status() {
    local service=$1
    local status=$2
    local pid=$3
    local port=$4
    
    if [ "$status" = "running" ]; then
        echo -e "${GREEN}✓${NC} $service: ${GREEN}运行中${NC} (PID: $pid, Port: $port)"
    else
        echo -e "${RED}✗${NC} $service: ${RED}未运行${NC}"
    fi
}

# 启动 API 服务
start_api() {
    if is_running "$API_PID_FILE"; then
        echo -e "${YELLOW}API 服务已在运行中${NC}"
        return 0
    fi
    
    if is_port_in_use "$API_PORT"; then
        echo -e "${RED}错误: 端口 $API_PORT 已被占用${NC}"
        echo -e "${YELLOW}提示: 请先停止占用该端口的服务，或修改脚本中的端口配置${NC}"
        return 1
    fi
    
    echo -e "${BLUE}启动 API 服务...${NC}"
    
    # 检查 Python 环境
    if ! command -v python &> /dev/null; then
        echo -e "${RED}错误: 未找到 Python${NC}"
        return 1
    fi
    
    # 启动 uvicorn
    nohup python -m uvicorn api.main:app \
        --host "$API_HOST" \
        --port "$API_PORT" \
        --reload \
        > "$API_LOG" 2>&1 &
    
    local pid=$!
    echo $pid > "$API_PID_FILE"
    
    # 等待服务启动
    sleep 2
    
    if is_running "$API_PID_FILE"; then
        echo -e "${GREEN}✓ API 服务启动成功${NC} (PID: $pid, Port: $API_PORT)"
        echo -e "${BLUE}  API 地址: http://$API_HOST:$API_PORT${NC}"
        echo -e "${BLUE}  API 文档: http://$API_HOST:$API_PORT/docs${NC}"
        echo -e "${BLUE}  日志文件: $API_LOG${NC}"
        return 0
    else
        echo -e "${RED}✗ API 服务启动失败${NC}"
        echo -e "${YELLOW}请查看日志: $API_LOG${NC}"
        rm -f "$API_PID_FILE"
        return 1
    fi
}

# 启动前端服务
start_frontend() {
    if is_running "$FRONTEND_PID_FILE"; then
        echo -e "${YELLOW}前端服务已在运行中${NC}"
        return 0
    fi
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        echo -e "${RED}错误: 前端目录不存在: $FRONTEND_DIR${NC}"
        return 1
    fi
    
    echo -e "${BLUE}启动前端服务...${NC}"
    
    # 检查 Node.js 环境
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}错误: 未找到 npm${NC}"
        return 1
    fi
    
    # 检查 node_modules
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo -e "${YELLOW}检测到未安装依赖，正在安装...${NC}"
        cd "$FRONTEND_DIR"
        npm install
        cd "$PROJECT_DIR"
    fi
    
    # 启动 Vite
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
    local pid=$!
    echo $pid > "$FRONTEND_PID_FILE"
    cd "$PROJECT_DIR"
    
    # 等待服务启动
    sleep 3
    
    if is_running "$FRONTEND_PID_FILE"; then
        # 尝试获取前端端口（Vite 默认 3000，可能自动递增）
        local frontend_port=$(grep -oP 'Local:\s+http://localhost:\K\d+' "$FRONTEND_LOG" 2>/dev/null | head -1 || echo "3000+")
        echo -e "${GREEN}✓ 前端服务启动成功${NC} (PID: $pid)"
        echo -e "${BLUE}  前端地址: http://localhost:$frontend_port${NC}"
        echo -e "${BLUE}  日志文件: $FRONTEND_LOG${NC}"
        return 0
    else
        echo -e "${RED}✗ 前端服务启动失败${NC}"
        echo -e "${YELLOW}请查看日志: $FRONTEND_LOG${NC}"
        rm -f "$FRONTEND_PID_FILE"
        return 1
    fi
}

# 停止 API 服务
stop_api() {
    local force_kill=${1:-false}
    
    if ! is_running "$API_PID_FILE"; then
        # 即使PID文件不存在，也检查端口是否被占用
        if is_port_in_use "$API_PORT"; then
            echo -e "${YELLOW}检测到端口 $API_PORT 仍被占用，尝试通过端口查找并停止进程...${NC}"
            local port_pid=$(lsof -ti :$API_PORT 2>/dev/null | head -1)
            if [ -n "$port_pid" ]; then
                echo -e "${BLUE}找到占用端口的进程 (PID: $port_pid)，正在停止...${NC}"
                kill -9 "$port_pid" 2>/dev/null || true
                sleep 1
                if ! ps -p "$port_pid" > /dev/null 2>&1; then
                    echo -e "${GREEN}✓ 已通过端口强制停止进程${NC}"
                    return 0
                fi
            fi
        else
            echo -e "${YELLOW}API 服务未运行${NC}"
            rm -f "$API_PID_FILE"
            return 0
        fi
    fi
    
    local pid=$(cat "$API_PID_FILE" 2>/dev/null || echo "")
    
    if [ -z "$pid" ] || ! ps -p "$pid" > /dev/null 2>&1; then
        # PID文件存在但进程不存在，清理文件
        rm -f "$API_PID_FILE"
        # 检查端口
        if is_port_in_use "$API_PORT"; then
            echo -e "${YELLOW}PID文件中的进程不存在，但端口仍被占用，尝试通过端口停止...${NC}"
            local port_pid=$(lsof -ti :$API_PORT 2>/dev/null | head -1)
            if [ -n "$port_pid" ]; then
                echo -e "${BLUE}找到占用端口的进程 (PID: $port_pid)，正在强制停止...${NC}"
                kill -9 "$port_pid" 2>/dev/null || true
                sleep 1
            fi
        fi
        return 0
    fi
    
    echo -e "${BLUE}停止 API 服务 (PID: $pid)...${NC}"
    
    # 如果指定了强制停止，直接kill -9
    if [ "$force_kill" = "true" ]; then
        echo -e "${YELLOW}强制停止模式，直接使用 kill -9...${NC}"
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    else
        # 尝试优雅停止
        kill "$pid" 2>/dev/null || true
        
        # 等待进程结束
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        # 如果还在运行，强制停止
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${YELLOW}优雅停止失败，强制停止 API 服务...${NC}"
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
        fi
    fi
    
    # 如果进程仍然存在，尝试通过端口查找并kill
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${RED}警告: PID $pid 仍然存在，尝试通过端口查找并强制停止...${NC}"
        local port_pid=$(lsof -ti :$API_PORT 2>/dev/null | head -1)
        if [ -n "$port_pid" ] && [ "$port_pid" != "$pid" ]; then
            echo -e "${YELLOW}发现另一个占用端口的进程 (PID: $port_pid)，正在停止...${NC}"
            kill -9 "$port_pid" 2>/dev/null || true
            sleep 1
        fi
        # 再次尝试kill -9原进程
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    fi
    
    rm -f "$API_PID_FILE"
    
    # 最终检查
    if ! ps -p "$pid" > /dev/null 2>&1 && ! is_port_in_use "$API_PORT"; then
        echo -e "${GREEN}✓ API 服务已停止${NC}"
        return 0
    else
        echo -e "${RED}✗ 停止 API 服务失败，进程可能仍在运行${NC}"
        if is_port_in_use "$API_PORT"; then
            echo -e "${YELLOW}提示: 端口 $API_PORT 仍被占用，请手动检查并停止相关进程${NC}"
            echo -e "${YELLOW}可以使用以下命令查找并停止:${NC}"
            echo -e "${YELLOW}  lsof -ti :$API_PORT | xargs kill -9${NC}"
        fi
        return 1
    fi
}

# 停止前端服务
stop_frontend() {
    local force_kill=${1:-false}
    
    if ! is_running "$FRONTEND_PID_FILE"; then
        echo -e "${YELLOW}前端服务未运行${NC}"
        rm -f "$FRONTEND_PID_FILE"
        return 0
    fi
    
    local pid=$(cat "$FRONTEND_PID_FILE" 2>/dev/null || echo "")
    
    if [ -z "$pid" ] || ! ps -p "$pid" > /dev/null 2>&1; then
        # PID文件存在但进程不存在，清理文件
        rm -f "$FRONTEND_PID_FILE"
        return 0
    fi
    
    echo -e "${BLUE}停止前端服务 (PID: $pid)...${NC}"
    
    # 如果指定了强制停止，直接kill -9
    if [ "$force_kill" = "true" ]; then
        echo -e "${YELLOW}强制停止模式，直接使用 kill -9...${NC}"
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    else
        # 尝试优雅停止
        kill "$pid" 2>/dev/null || true
        
        # 等待进程结束
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        # 如果还在运行，强制停止
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${YELLOW}优雅停止失败，强制停止前端服务...${NC}"
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
        fi
    fi
    
    # 如果进程仍然存在，尝试查找所有相关进程（包括子进程）
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${RED}警告: PID $pid 仍然存在，尝试停止所有相关进程...${NC}"
        # 查找并停止所有子进程
        local child_pids=$(pgrep -P "$pid" 2>/dev/null || true)
        if [ -n "$child_pids" ]; then
            echo -e "${YELLOW}发现子进程，正在停止...${NC}"
            echo "$child_pids" | xargs kill -9 2>/dev/null || true
            sleep 1
        fi
        # 再次尝试kill -9原进程
        kill -9 "$pid" 2>/dev/null || true
        sleep 1
    fi
    
    rm -f "$FRONTEND_PID_FILE"
    
    # 最终检查
    if ! ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 前端服务已停止${NC}"
        return 0
    else
        echo -e "${RED}✗ 停止前端服务失败，进程可能仍在运行${NC}"
        echo -e "${YELLOW}提示: 请手动检查并停止相关进程${NC}"
        echo -e "${YELLOW}可以使用以下命令查找并停止:${NC}"
        echo -e "${YELLOW}  ps aux | grep -E 'vite|node.*frontend' | grep -v grep${NC}"
        return 1
    fi
}

# 查询运行状态
status() {
    echo -e "${BLUE}=== DAAS Alpha 服务状态 ===${NC}"
    echo ""
    
    # API 状态
    if is_running "$API_PID_FILE"; then
        local api_pid=$(cat "$API_PID_FILE")
        print_status "API 服务" "running" "$api_pid" "$API_PORT"
        
        # 检查端口是否真的在监听
        if is_port_in_use "$API_PORT"; then
            echo -e "  ${GREEN}端口 $API_PORT 正在监听${NC}"
        else
            echo -e "  ${YELLOW}警告: 端口 $API_PORT 未在监听${NC}"
        fi
    else
        print_status "API 服务" "stopped" "" "$API_PORT"
    fi
    
    echo ""
    
    # 前端状态
    if is_running "$FRONTEND_PID_FILE"; then
        local frontend_pid=$(cat "$FRONTEND_PID_FILE")
        # 尝试获取实际端口
        local frontend_port=$(grep -oP 'Local:\s+http://localhost:\K\d+' "$FRONTEND_LOG" 2>/dev/null | head -1 || echo "未知")
        print_status "前端服务" "running" "$frontend_pid" "$frontend_port"
    else
        print_status "前端服务" "stopped" "" ""
    fi
    
    echo ""
    
    # 显示日志文件位置
    echo -e "${BLUE}日志文件:${NC}"
    echo -e "  API:     $API_LOG"
    echo -e "  前端:    $FRONTEND_LOG"
    echo ""
}

# 启动所有服务
start_all() {
    echo -e "${BLUE}=== 启动所有服务 ===${NC}"
    echo ""
    
    start_api
    echo ""
    start_frontend
    echo ""
    
    echo -e "${GREEN}=== 启动完成 ===${NC}"
    echo ""
    status
}

# 停止所有服务
stop_all() {
    local force_kill=${1:-false}
    echo -e "${BLUE}=== 停止所有服务 ===${NC}"
    echo ""
    
    stop_frontend "$force_kill"
    echo ""
    stop_api "$force_kill"
    echo ""
    
    echo -e "${GREEN}=== 停止完成 ===${NC}"
}

# 重启服务
restart() {
    echo -e "${BLUE}=== 重启服务 ===${NC}"
    echo ""
    
    stop_all
    echo ""
    sleep 2
    start_all
}

# 显示帮助信息
show_help() {
    echo -e "${BLUE}DAAS Alpha 服务管理脚本${NC}"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start         启动所有服务 (API + 前端)"
    echo "  start-api     仅启动 API 服务"
    echo "  start-frontend 仅启动前端服务"
    echo "  stop          停止所有服务（优雅停止，失败时自动强制停止）"
    echo "  stop --force  强制停止所有服务（直接使用 kill -9）"
    echo "  stop-api      仅停止 API 服务"
    echo "  stop-api --force 强制停止 API 服务"
    echo "  stop-frontend 仅停止前端服务"
    echo "  stop-frontend --force 强制停止前端服务"
    echo "  restart       重启所有服务"
    echo "  status        查询服务运行状态"
    echo "  help          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start       # 启动所有服务"
    echo "  $0 status     # 查看服务状态"
    echo "  $0 stop        # 停止所有服务"
    echo "  $0 restart    # 重启所有服务"
    echo ""
}

# 主函数
main() {
    local command="${1:-help}"
    local force_flag="${2:-}"
    local force_kill=false
    
    # 检查是否指定了强制停止标志
    if [ "$force_flag" = "--force" ] || [ "$force_flag" = "-f" ]; then
        force_kill=true
    fi
    
    case "$command" in
        start)
            start_all
            ;;
        start-api)
            start_api
            ;;
        start-frontend)
            start_frontend
            ;;
        stop)
            stop_all "$force_kill"
            ;;
        stop-api)
            stop_api "$force_kill"
            ;;
        stop-frontend)
            stop_frontend "$force_kill"
            ;;
        restart)
            restart
            ;;
        status)
            status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}错误: 未知命令 '$command'${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
