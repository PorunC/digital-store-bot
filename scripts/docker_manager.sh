#!/bin/bash

# ==============================================================================
# Docker 服务管理脚本 (智能Traefik保护)
# ==============================================================================
#
# 高级Docker服务管理脚本，具有以下功能：
# - 智能检测和保护Traefik容器
# - 支持多种重启策略
# - 自动备份和恢复
# - 详细的日志和监控
# - 零停机部署选项
#
# 使用方法:
# ./scripts/docker_manager.sh [命令] [选项]
#
# ==============================================================================

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups/containers"
LOG_FILE="$PROJECT_DIR/logs/docker_manager.log"

# 创建必要的目录
mkdir -p "$BACKUP_DIR" "$(dirname "$LOG_FILE")"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# 日志函数
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
    log "INFO" "$1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    log "SUCCESS" "$1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
    log "WARNING" "$1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    log "ERROR" "$1"
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo -e "${PURPLE}[DEBUG]${NC} $1"
        log "DEBUG" "$1"
    fi
}

# 检查系统要求
check_prerequisites() {
    log_info "检查系统要求..."
    
    local missing_deps=()
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        missing_deps+=("docker-compose")
    fi
    
    if ! command -v jq &> /dev/null; then
        log_warning "建议安装 jq 以获得更好的JSON处理能力"
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "缺少依赖: ${missing_deps[*]}"
        exit 1
    fi
    
    # 确定compose命令
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    log_success "系统要求检查通过"
}

# 获取Traefik容器信息
get_traefik_info() {
    local container_id
    container_id=$(docker ps -q --filter "name=traefik" 2>/dev/null || echo "")
    
    if [ -n "$container_id" ]; then
        echo "$container_id"
        return 0
    else
        return 1
    fi
}

# 备份Traefik配置
backup_traefik() {
    log_info "备份Traefik配置..."
    
    local traefik_id
    if traefik_id=$(get_traefik_info); then
        local backup_file="$BACKUP_DIR/traefik_backup_$(date +%Y%m%d_%H%M%S).tar"
        
        # 备份Traefik容器数据
        docker export "$traefik_id" > "$backup_file"
        
        # 备份Let's Encrypt证书
        if docker volume ls | grep -q "traefik_letsencrypt"; then
            docker run --rm -v traefik_letsencrypt:/data -v "$BACKUP_DIR":/backup alpine tar czf "/backup/letsencrypt_$(date +%Y%m%d_%H%M%S).tar.gz" -C /data .
        fi
        
        log_success "Traefik备份完成: $backup_file"
        return 0
    else
        log_warning "Traefik容器未运行，跳过备份"
        return 1
    fi
}

# 创建Traefik网络快照
create_network_snapshot() {
    log_info "创建网络快照..."
    
    local snapshot_file="$BACKUP_DIR/network_snapshot_$(date +%Y%m%d_%H%M%S).json"
    
    # 保存网络信息
    docker network ls --format "json" > "$snapshot_file"
    
    # 保存容器网络连接信息
    docker ps --format "json" | jq -s '.' >> "$snapshot_file"
    
    log_success "网络快照已保存: $snapshot_file"
}

# 获取服务列表
get_services() {
    local exclude_traefik="$1"
    local services
    
    services=$($COMPOSE_CMD config --services)
    
    if [ "$exclude_traefik" = "true" ]; then
        services=$(echo "$services" | grep -v "traefik")
    fi
    
    echo "$services"
}

# 检查服务健康状态
check_service_health() {
    local service="$1"
    local container_name
    
    # 获取容器名称
    case "$service" in
        "bot") container_name="digital_store_bot" ;;
        "admin") container_name="admin_panel" ;;
        "scheduler") container_name="task_scheduler" ;;
        "postgres") container_name="postgres" ;;
        "redis") container_name="redis" ;;
        "traefik") container_name="traefik" ;;
        *) container_name="$service" ;;
    esac
    
    local health_status
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "no-healthcheck")
    
    case "$health_status" in
        "healthy") return 0 ;;
        "unhealthy") return 1 ;;
        "starting") return 2 ;;
        "no-healthcheck") return 3 ;;
        *) return 1 ;;
    esac
}

# 等待服务就绪
wait_for_services() {
    local services="$1"
    local timeout="${2:-300}"
    
    log_info "等待服务就绪（超时: ${timeout}s）..."
    
    local start_time=$(date +%s)
    local ready_services=()
    local pending_services=($services)
    
    while [ ${#pending_services[@]} -gt 0 ] && [ $(($(date +%s) - start_time)) -lt $timeout ]; do
        local new_pending=()
        
        for service in "${pending_services[@]}"; do
            if check_service_health "$service"; then
                ready_services+=("$service")
                log_success "服务 $service 已就绪"
            elif [ $? -eq 2 ]; then
                new_pending+=("$service")
                log_debug "服务 $service 正在启动..."
            elif [ $? -eq 3 ]; then
                ready_services+=("$service")
                log_info "服务 $service 无健康检查，假定已就绪"
            else
                new_pending+=("$service")
                log_warning "服务 $service 健康检查失败"
            fi
        done
        
        pending_services=("${new_pending[@]}")
        
        if [ ${#pending_services[@]} -gt 0 ]; then
            sleep 5
        fi
    done
    
    if [ ${#pending_services[@]} -eq 0 ]; then
        log_success "所有服务已就绪"
        return 0
    else
        log_error "以下服务未能及时就绪: ${pending_services[*]}"
        return 1
    fi
}

# 滚动重启服务
rolling_restart() {
    local services="$1"
    local build_flag="$2"
    
    log_info "开始滚动重启服务..."
    
    # 定义重启顺序（数据库服务优先）
    local restart_order=("redis" "postgres" "bot" "scheduler" "admin")
    local services_array=($services)
    
    for service in "${restart_order[@]}"; do
        if [[ " ${services_array[*]} " =~ " ${service} " ]]; then
            log_info "重启服务: $service"
            
            if [ "$build_flag" = "true" ]; then
                $COMPOSE_CMD up -d --build --no-deps "$service"
            else
                $COMPOSE_CMD restart "$service"
            fi
            
            # 等待单个服务就绪
            if ! wait_for_services "$service" 60; then
                log_error "服务 $service 重启失败"
                return 1
            fi
            
            sleep 2
        fi
    done
    
    log_success "滚动重启完成"
}

# 零停机重启
zero_downtime_restart() {
    local services="$1"
    local build_flag="$2"
    
    log_info "开始零停机重启..."
    
    # 检查Traefik是否运行
    if ! get_traefik_info > /dev/null; then
        log_error "零停机重启需要Traefik运行"
        return 1
    fi
    
    # 为关键服务创建临时副本
    local critical_services=("bot" "admin")
    
    for service in "${critical_services[@]}"; do
        if [[ "$services" =~ $service ]]; then
            log_info "为 $service 创建临时副本..."
            
            # 启动临时容器
            $COMPOSE_CMD up -d --scale "$service=2" "$service"
            
            # 等待新实例就绪
            sleep 10
            
            # 停止原始实例
            local original_container
            original_container=$(docker ps --filter "label=com.docker.compose.service=$service" --format "{{.Names}}" | head -1)
            
            if [ -n "$original_container" ]; then
                docker stop "$original_container"
                sleep 5
                docker rm "$original_container"
            fi
            
            # 恢复正常副本数
            $COMPOSE_CMD up -d --scale "$service=1" "$service"
        fi
    done
    
    log_success "零停机重启完成"
}

# 显示详细状态
show_detailed_status() {
    log_info "系统状态详情:"
    echo
    
    # Docker系统信息
    echo -e "${CYAN}=== Docker 系统信息 ===${NC}"
    docker system df
    echo
    
    # 容器状态
    echo -e "${CYAN}=== 容器状态 ===${NC}"
    $COMPOSE_CMD ps
    echo
    
    # Traefik状态
    echo -e "${CYAN}=== Traefik 状态 ===${NC}"
    if get_traefik_info > /dev/null; then
        docker ps --filter "name=traefik" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo
        
        # Traefik路由信息
        if command -v curl &> /dev/null; then
            echo -e "${CYAN}=== Traefik 路由 ===${NC}"
            curl -s http://localhost:8080/api/http/routers 2>/dev/null | jq -r '.[] | "\(.rule) -> \(.service)"' 2>/dev/null || echo "无法获取路由信息"
            echo
        fi
    else
        echo "Traefik 未运行"
        echo
    fi
    
    # 资源使用情况
    echo -e "${CYAN}=== 资源使用情况 ===${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    echo
    
    # 日志摘要
    echo -e "${CYAN}=== 最近错误日志 ===${NC}"
    if [ -f "$LOG_FILE" ]; then
        tail -5 "$LOG_FILE" | grep -E "(ERROR|WARNING)" || echo "无最近错误"
    else
        echo "日志文件不存在"
    fi
}

# 清理和维护
cleanup_and_maintenance() {
    log_info "执行清理和维护..."
    
    # 清理未使用的容器
    log_info "清理未使用的容器..."
    docker container prune -f
    
    # 清理未使用的镜像
    log_info "清理未使用的镜像..."
    docker image prune -f
    
    # 清理未使用的网络
    log_info "清理未使用的网络..."
    docker network prune -f
    
    # 清理未使用的卷（谨慎使用）
    if [[ "${PRUNE_VOLUMES:-false}" == "true" ]]; then
        log_warning "清理未使用的卷..."
        docker volume prune -f
    fi
    
    # 清理旧的备份文件（保留最近7天）
    log_info "清理旧备份文件..."
    find "$BACKUP_DIR" -name "*.tar*" -mtime +7 -delete 2>/dev/null || true
    
    log_success "清理和维护完成"
}

# 显示帮助信息
show_help() {
    cat << EOF
Docker 服务管理脚本 (智能Traefik保护)

用法: $0 <命令> [选项]

命令:
  restart           标准重启（保持Traefik）
  rolling           滚动重启（逐个重启服务）
  zero-downtime     零停机重启（需要Traefik）
  status            显示详细状态
  backup            备份Traefik和配置
  cleanup           清理和维护
  help              显示此帮助

选项:
  --all             操作所有服务（除Traefik）
  --app             仅应用服务 (bot, admin, scheduler)
  --db              仅数据库服务 (postgres, redis)
  --monitoring      仅监控服务 (prometheus, grafana)
  --build           重新构建镜像
  --include-traefik 包含Traefik（谨慎使用）
  --debug           启用调试输出

环境变量:
  DEBUG=true        启用调试模式
  PRUNE_VOLUMES=true 清理时包含卷

示例:
  $0 restart --app             # 重启应用服务
  $0 rolling --all --build     # 滚动重启并重建
  $0 zero-downtime --app       # 零停机重启应用
  $0 backup                    # 备份Traefik配置
  $0 status                    # 显示详细状态
  $0 cleanup                   # 清理和维护

EOF
}

# 主函数
main() {
    local command=""
    local scope=""
    local build_flag="false"
    local include_traefik="false"
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            restart|rolling|zero-downtime|status|backup|cleanup|help)
                command="$1"
                shift
                ;;
            --all)
                scope="all"
                shift
                ;;
            --app)
                scope="app"
                shift
                ;;
            --db)
                scope="db"
                shift
                ;;
            --monitoring)
                scope="monitoring"
                shift
                ;;
            --build)
                build_flag="true"
                shift
                ;;
            --include-traefik)
                include_traefik="true"
                shift
                ;;
            --debug)
                export DEBUG="true"
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查命令
    if [ -z "$command" ]; then
        log_error "请指定命令"
        show_help
        exit 1
    fi
    
    # 显示帮助
    if [ "$command" = "help" ]; then
        show_help
        exit 0
    fi
    
    # 检查系统要求
    check_prerequisites
    
    # 执行命令
    case "$command" in
        status)
            show_detailed_status
            ;;
        backup)
            backup_traefik
            create_network_snapshot
            ;;
        cleanup)
            cleanup_and_maintenance
            ;;
        restart|rolling|zero-downtime)
            # 确定服务范围
            if [ -z "$scope" ]; then
                log_error "请指定服务范围: --all, --app, --db, 或 --monitoring"
                exit 1
            fi
            
            # 获取服务列表
            local services=""
            case "$scope" in
                all)
                    services=$(get_services "$([ "$include_traefik" = "false" ] && echo "true" || echo "false")")
                    ;;
                app)
                    services="bot admin scheduler"
                    ;;
                db)
                    services="postgres redis"
                    ;;
                monitoring)
                    services="prometheus grafana loki promtail"
                    ;;
            esac
            
            log_info "命令: $command"
            log_info "服务: $services"
            log_info "重建: $build_flag"
            
            # 创建备份（如果包含关键服务）
            if [[ "$services" =~ (bot|admin|postgres) ]]; then
                backup_traefik
            fi
            
            # 执行相应的重启策略
            case "$command" in
                restart)
                    $COMPOSE_CMD stop $services
                    sleep 2
                    if [ "$build_flag" = "true" ]; then
                        $COMPOSE_CMD up -d --build $services
                    else
                        $COMPOSE_CMD up -d $services
                    fi
                    wait_for_services "$services"
                    ;;
                rolling)
                    rolling_restart "$services" "$build_flag"
                    ;;
                zero-downtime)
                    zero_downtime_restart "$services" "$build_flag"
                    ;;
            esac
            
            log_success "操作完成"
            show_detailed_status
            ;;
    esac
}

# 错误处理
trap 'log_error "脚本异常退出"; exit 1' ERR
trap 'log_info "脚本被中断"; exit 130' INT TERM

# 运行主函数
main "$@"