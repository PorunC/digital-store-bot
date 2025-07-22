#!/bin/bash

# =============================================================================
# Digital Store Bot v2 - Health Check Script
# =============================================================================

set -e

# Configuration
HEALTH_ENDPOINT="http://localhost:8000/health"
TIMEOUT=10
MAX_RETRIES=3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "[INFO] $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if service is running
check_service() {
    local service_type="${SERVICE_TYPE:-bot}"
    
    case "$service_type" in
        "bot")
            check_bot_health
            ;;
        "admin")
            check_admin_health
            ;;
        "scheduler")
            check_scheduler_health
            ;;
        "worker")
            check_worker_health
            ;;
        *)
            log_error "Unknown service type: $service_type"
            exit 1
            ;;
    esac
}

# Check bot health
check_bot_health() {
    log_info "Checking bot health..."
    
    # Check if bot process is running
    if ! pgrep -f "python -m src.main" > /dev/null; then
        log_error "Bot process not running"
        exit 1
    fi
    
    # Check HTTP health endpoint
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -f -s --connect-timeout $TIMEOUT "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
            log_success "Bot health check passed"
            return 0
        fi
        
        if [ $i -eq $MAX_RETRIES ]; then
            log_error "Bot health endpoint not responding after $MAX_RETRIES attempts"
            exit 1
        fi
        
        log_warning "Health check attempt $i/$MAX_RETRIES failed, retrying..."
        sleep 2
    done
}

# Check admin panel health
check_admin_health() {
    log_info "Checking admin panel health..."
    
    # Check if admin process is running
    if ! pgrep -f "src.presentation.web.admin_panel" > /dev/null; then
        log_error "Admin panel process not running"
        exit 1
    fi
    
    # Check HTTP health endpoint (admin usually runs on port 8080)
    local admin_endpoint="http://localhost:8080/health"
    
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -f -s --connect-timeout $TIMEOUT "$admin_endpoint" > /dev/null 2>&1; then
            log_success "Admin panel health check passed"
            return 0
        fi
        
        if [ $i -eq $MAX_RETRIES ]; then
            log_error "Admin panel health endpoint not responding after $MAX_RETRIES attempts"
            exit 1
        fi
        
        log_warning "Health check attempt $i/$MAX_RETRIES failed, retrying..."
        sleep 2
    done
}

# Check scheduler health
check_scheduler_health() {
    log_info "Checking scheduler health..."
    
    # Check if scheduler process is running
    if ! pgrep -f "src.infrastructure.background_tasks.scheduler" > /dev/null; then
        log_error "Scheduler process not running"
        exit 1
    fi
    
    # Check if scheduler is responsive (check recent activity)
    local log_file="/app/logs/scheduler.log"
    
    if [ -f "$log_file" ]; then
        # Check if there's been activity in the last 5 minutes
        local recent_activity=$(find "$log_file" -newermt "5 minutes ago" | wc -l)
        
        if [ "$recent_activity" -eq 0 ]; then
            log_warning "No recent scheduler activity detected"
        else
            log_success "Scheduler is active"
        fi
    else
        log_warning "Scheduler log file not found"
    fi
    
    log_success "Scheduler health check passed"
}

# Check worker health
check_worker_health() {
    log_info "Checking worker health..."
    
    # Check if worker process is running
    if ! pgrep -f "src.infrastructure.background_tasks.worker" > /dev/null; then
        log_error "Worker process not running"
        exit 1
    fi
    
    log_success "Worker health check passed"
}

# Check database connectivity
check_database() {
    log_info "Checking database connectivity..."
    
    python3 -c "
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_db():
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print('DATABASE_URL not set')
            return False
            
        engine = create_async_engine(database_url, pool_timeout=5)
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT 1'))
            row = result.fetchone()
            if row and row[0] == 1:
                print('Database connection successful')
                await engine.dispose()
                return True
        await engine.dispose()
        return False
    except Exception as e:
        print(f'Database check failed: {e}')
        return False

success = asyncio.run(check_db())
sys.exit(0 if success else 1)
"
    
    if [ $? -eq 0 ]; then
        log_success "Database connectivity check passed"
    else
        log_error "Database connectivity check failed"
        exit 1
    fi
}

# Check Redis connectivity
check_redis() {
    log_info "Checking Redis connectivity..."
    
    python3 -c "
import redis
import sys
import os
from urllib.parse import urlparse

try:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    parsed = urlparse(redis_url)
    
    r = redis.Redis(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 6379,
        db=int(parsed.path.lstrip('/')) if parsed.path else 0,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    
    # Test connection
    r.ping()
    print('Redis connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Redis check failed: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "Redis connectivity check passed"
    else
        log_error "Redis connectivity check failed"
        exit 1
    fi
}

# Check disk space
check_disk_space() {
    log_info "Checking disk space..."
    
    # Check available disk space (warn if less than 1GB)
    local available_space=$(df /app | awk 'NR==2 {print $4}')
    local min_space=1048576  # 1GB in KB
    
    if [ "$available_space" -lt "$min_space" ]; then
        log_warning "Low disk space: $(($available_space / 1024))MB available"
    else
        log_success "Disk space check passed: $(($available_space / 1024))MB available"
    fi
}

# Check memory usage
check_memory() {
    log_info "Checking memory usage..."
    
    # Get memory usage percentage
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$memory_usage" -gt 90 ]; then
        log_warning "High memory usage: ${memory_usage}%"
    else
        log_success "Memory usage check passed: ${memory_usage}%"
    fi
}

# Main health check routine
main() {
    log_info "=== Digital Store Bot v2 Health Check ==="
    
    # Basic service health check
    check_service
    
    # Infrastructure checks (only if not in minimal mode)
    if [ "${HEALTH_CHECK_MINIMAL:-false}" != "true" ]; then
        check_database
        check_redis
        check_disk_space
        check_memory
    fi
    
    log_success "=== All health checks passed ==="
    exit 0
}

# Handle timeout
timeout_handler() {
    log_error "Health check timed out"
    exit 1
}

# Set timeout
trap timeout_handler ALRM
alarm() { sleep $1 && kill -ALRM $$ & }
alarm 30  # 30 second timeout

# Run health checks
main "$@"