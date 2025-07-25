#!/bin/bash

# ==============================================================================
# Docker Restart Script (Excluding Traefik)
# ==============================================================================
# 
# 这个脚本用于重启Docker服务时保持Traefik容器运行
# 适用于生产环境中需要保持反向代理持续运行的场景
#
# 使用方法:
# ./scripts/restart_without_traefik.sh [选项]
#
# 选项:
#   --all         重启所有服务（除了Traefik）
#   --app         只重启应用服务 (bot, admin, scheduler)
#   --db          只重启数据库服务 (postgres, redis)
#   --monitoring  重启监控服务 (prometheus, grafana, loki, promtail)
#   --build       重新构建镜像再重启
#   --help        显示帮助信息
#
# ==============================================================================

set -euo pipefail

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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker和Docker Compose是否可用
check_prerequisites() {
    log_info "检查系统要求..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或不在PATH中"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装或不在PATH中"
        exit 1
    fi
    
    # 优先使用 docker compose，降级到 docker-compose
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    log_success "Docker 和 Docker Compose 检查通过"
}

# 检查Traefik容器状态
check_traefik_status() {
    log_info "检查Traefik容器状态..."
    
    if docker ps --format "table {{.Names}}" | grep -q "traefik"; then
        log_success "Traefik容器正在运行"
        return 0
    else
        log_warning "Traefik容器未运行"
        return 1
    fi
}

# 停止指定服务（排除Traefik）
stop_services() {
    local services="$1"
    log_info "停止服务: $services"
    
    if [ "$services" = "all" ]; then
        # 获取所有服务名称，排除 traefik
        local all_services
        all_services=$($COMPOSE_CMD config --services | grep -v "traefik" | tr '\n' ' ')
        log_info "停止所有服务（除Traefik）: $all_services"
        $COMPOSE_CMD stop $all_services
    else
        $COMPOSE_CMD stop $services
    fi
}

# 启动指定服务
start_services() {
    local services="$1"
    local build_flag="$2"
    
    log_info "启动服务: $services"
    
    if [ "$build_flag" = "true" ]; then
        log_info "重新构建镜像..."
        if [ "$services" = "all" ]; then
            local all_services
            all_services=$($COMPOSE_CMD config --services | grep -v "traefik" | tr '\n' ' ')
            $COMPOSE_CMD up -d --build $all_services
        else
            $COMPOSE_CMD up -d --build $services
        fi
    else
        if [ "$services" = "all" ]; then
            local all_services
            all_services=$($COMPOSE_CMD config --services | grep -v "traefik" | tr '\n' ' ')
            $COMPOSE_CMD up -d $all_services
        else
            $COMPOSE_CMD up -d $services
        fi
    fi
}

# 等待服务健康检查
wait_for_health() {
    local services="$1"
    log_info "等待服务健康检查..."
    
    # 等待最多5分钟
    local timeout=300
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        local unhealthy_services=""
        
        # 检查每个服务的健康状态
        for service in $services; do
            # 跳过没有健康检查的服务
            if [ "$service" = "scheduler" ] || [ "$service" = "prometheus" ] || [ "$service" = "grafana" ] || [ "$service" = "loki" ] || [ "$service" = "promtail" ]; then
                continue
            fi
            
            local health_status
            health_status=$(docker inspect --format='{{.State.Health.Status}}' "${service}" 2>/dev/null || echo "no-healthcheck")
            
            if [ "$health_status" != "healthy" ] && [ "$health_status" != "no-healthcheck" ]; then
                unhealthy_services="$unhealthy_services $service"
            fi
        done
        
        if [ -z "$unhealthy_services" ]; then
            log_success "所有服务健康检查通过"
            return 0
        fi
        
        log_info "等待服务变为健康状态:$unhealthy_services (${elapsed}s/${timeout}s)"
        sleep 10
        elapsed=$((elapsed + 10))
    done
    
    log_warning "健康检查超时，但服务可能仍在启动中"
    return 1
}

# 显示服务状态
show_status() {
    log_info "当前服务状态:"
    echo
    $COMPOSE_CMD ps
    echo
    
    log_info "Traefik容器状态:"
    docker ps --filter "name=traefik" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo
}

# 显示帮助信息
show_help() {
    cat << EOF
Docker重启脚本 (保持Traefik运行)

用法: $0 [选项]

选项:
  --all         重启所有服务（除了Traefik）
  --app         只重启应用服务 (bot, admin, scheduler)
  --db          只重启数据库服务 (postgres, redis)
  --monitoring  重启监控服务 (prometheus, grafana, loki, promtail)
  --build       重新构建镜像再重启
  --help        显示此帮助信息

示例:
  $0 --all              # 重启所有服务（保持Traefik运行）
  $0 --app              # 只重启应用服务
  $0 --app --build      # 重新构建并重启应用服务
  $0 --db               # 只重启数据库服务
  $0 --monitoring       # 重启监控服务

注意:
- Traefik容器始终保持运行，确保反向代理服务不中断
- 使用 --build 选项会重新构建Docker镜像
- 脚本会等待服务健康检查通过

EOF
}

# 主函数
main() {
    local action=""
    local build_flag="false"
    local services=""
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                action="all"
                services="all"
                shift
                ;;
            --app)
                action="app"
                services="bot admin scheduler"
                shift
                ;;
            --db)
                action="db"
                services="postgres redis"
                shift
                ;;
            --monitoring)
                action="monitoring"
                services="prometheus grafana loki promtail"
                shift
                ;;
            --build)
                build_flag="true"
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 如果没有指定动作，显示帮助
    if [ -z "$action" ]; then
        log_error "请指定要重启的服务"
        show_help
        exit 1
    fi
    
    log_info "开始重启Docker服务 (保持Traefik运行)"
    log_info "动作: $action"
    log_info "重新构建: $build_flag"
    echo
    
    # 检查系统要求
    check_prerequisites
    
    # 检查Traefik状态
    traefik_was_running=false
    if check_traefik_status; then
        traefik_was_running=true
    fi
    
    # 显示当前状态
    show_status
    
    # 确认操作
    log_warning "即将重启服务: $services"
    if [ "$traefik_was_running" = "true" ]; then
        log_info "Traefik将保持运行状态"
    else
        log_warning "Traefik当前未运行，但不会被此脚本启动"
    fi
    
    read -p "确认继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "操作已取消"
        exit 0
    fi
    
    # 停止服务
    stop_services "$services"
    
    # 等待服务完全停止
    log_info "等待服务完全停止..."
    sleep 5
    
    # 启动服务
    start_services "$services" "$build_flag"
    
    # 等待健康检查
    if [ "$action" = "app" ] || [ "$action" = "all" ]; then
        wait_for_health "$services"
    else
        log_info "跳过健康检查（数据库/监控服务）"
        sleep 10
    fi
    
    # 显示最终状态
    echo
    log_success "服务重启完成！"
    show_status
    
    # 最终检查Traefik
    if check_traefik_status; then
        log_success "Traefik容器保持运行状态 ✓"
    else
        log_error "Traefik容器未运行！可能需要手动启动"
    fi
}

# 捕获中断信号
trap 'log_error "脚本被中断"; exit 1' INT TERM

# 运行主函数
main "$@"