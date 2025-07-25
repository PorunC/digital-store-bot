#!/bin/bash

# ==============================================================================
# 快速重启脚本 (保持Traefik运行)
# ==============================================================================
# 
# 这是一个简化版本的重启脚本，用于快速重启应用服务
# 适用于开发和测试环境
#
# 使用方法:
# ./scripts/quick_restart.sh
#
# ==============================================================================

set -euo pipefail

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔄 快速重启Docker服务 (保持Traefik运行)${NC}"
echo

# 确定使用的compose命令
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# 获取所有服务，排除traefik
ALL_SERVICES=$($COMPOSE_CMD config --services | grep -v "traefik" | tr '\n' ' ')

echo -e "${BLUE}📋 将重启的服务:${NC} $ALL_SERVICES"
echo

# 停止所有服务（除了traefik）
echo -e "${BLUE}⏹️  停止服务...${NC}"
$COMPOSE_CMD stop $ALL_SERVICES

# 启动所有服务（除了traefik）
echo -e "${BLUE}▶️  启动服务...${NC}"
$COMPOSE_CMD up -d $ALL_SERVICES

# 显示状态
echo
echo -e "${GREEN}✅ 重启完成！${NC}"
echo
echo -e "${BLUE}📊 当前状态:${NC}"
$COMPOSE_CMD ps

# 检查Traefik状态
echo
if docker ps --format "table {{.Names}}" | grep -q "traefik"; then
    echo -e "${GREEN}✅ Traefik保持运行状态${NC}"
else
    echo -e "${BLUE}ℹ️  Traefik未运行${NC}"
fi