#!/bin/bash

# Daily Runner Cron Setup Script
# 自动配置cron任务，支持macOS和Linux

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CRON_SCRIPT="$PROJECT_ROOT/scripts/daily_runner_cron.py"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/daily_runner_cron.log"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 检测Python路径
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD=$(which python3)
elif command -v python &> /dev/null; then
    PYTHON_CMD=$(which python)
else
    echo -e "${RED}错误: 未找到Python解释器${NC}"
    exit 1
fi

echo -e "${BLUE}DAAS Alpha - Daily Runner Cron Setup${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""
echo -e "项目根目录: ${GREEN}$PROJECT_ROOT${NC}"
echo -e "Cron脚本: ${GREEN}$CRON_SCRIPT${NC}"
echo -e "Python路径: ${GREEN}$PYTHON_CMD${NC}"
echo -e "日志文件: ${GREEN}$LOG_FILE${NC}"
echo ""

# 检查cron脚本是否存在
if [ ! -f "$CRON_SCRIPT" ]; then
    echo -e "${RED}错误: Cron脚本不存在: $CRON_SCRIPT${NC}"
    exit 1
fi

# 确保cron脚本可执行
chmod +x "$CRON_SCRIPT"

# 构建cron命令
# 每天17:30执行
CRON_TIME="30 17"
CRON_CMD="$PYTHON_CMD $CRON_SCRIPT >> $LOG_FILE 2>&1"
CRON_ENTRY="$CRON_TIME * * * $CRON_CMD"

echo -e "${YELLOW}准备添加以下cron任务:${NC}"
echo -e "${GREEN}$CRON_ENTRY${NC}"
echo ""

# 检测操作系统
OS_TYPE=""
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macOS"
    CRONTAB_CMD="crontab"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="Linux"
    CRONTAB_CMD="crontab"
else
    echo -e "${RED}错误: 不支持的操作系统: $OSTYPE${NC}"
    exit 1
fi

echo -e "检测到操作系统: ${GREEN}$OS_TYPE${NC}"
echo ""

# 读取现有的cron任务
TEMP_CRON=$(mktemp)
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# 检查是否已存在相同的任务
if grep -q "$CRON_SCRIPT" "$TEMP_CRON" 2>/dev/null; then
    echo -e "${YELLOW}检测到已存在的cron任务，将更新它${NC}"
    # 删除旧的任务
    grep -v "$CRON_SCRIPT" "$TEMP_CRON" > "${TEMP_CRON}.new" || true
    mv "${TEMP_CRON}.new" "$TEMP_CRON"
fi

# 添加新任务
echo "$CRON_ENTRY" >> "$TEMP_CRON"

# 安装cron任务
echo -e "${YELLOW}正在安装cron任务...${NC}"
crontab "$TEMP_CRON"
rm "$TEMP_CRON"

echo ""
echo -e "${GREEN}✓ Cron任务已成功安装${NC}"
echo ""
echo -e "查看cron任务: ${BLUE}crontab -l${NC}"
echo -e "编辑cron任务: ${BLUE}crontab -e${NC}"
echo -e "删除cron任务: ${BLUE}crontab -r${NC}"
echo ""
echo -e "查看日志: ${BLUE}tail -f $LOG_FILE${NC}"
echo ""

# 验证安装
echo -e "${YELLOW}验证安装...${NC}"
if crontab -l | grep -q "$CRON_SCRIPT"; then
    echo -e "${GREEN}✓ 验证成功: cron任务已安装${NC}"
    echo ""
    echo -e "当前cron任务列表:"
    crontab -l | grep -A 1 -B 1 "$CRON_SCRIPT" || crontab -l
else
    echo -e "${RED}✗ 验证失败: cron任务未找到${NC}"
    exit 1
fi
