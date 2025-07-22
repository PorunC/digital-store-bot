#!/bin/bash

# =============================================================================
# Digital Store Bot v2 - Container Startup Script
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Wait for database to be ready
wait_for_database() {
    log_info "Waiting for database to be ready..."
    
    # Extract database details from DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ]; then
        log_warning "Could not parse database connection details, skipping wait"
        return 0
    fi
    
    # Wait for database connection
    for i in {1..30}; do
        if nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; then
            log_success "Database is ready!"
            return 0
        fi
        log_info "Database not ready, waiting... ($i/30)"
        sleep 2
    done
    
    log_error "Database did not become ready in time"
    exit 1
}

# Wait for Redis to be ready
wait_for_redis() {
    log_info "Waiting for Redis to be ready..."
    
    # Extract Redis details from REDIS_URL
    REDIS_HOST=$(echo $REDIS_URL | sed -n 's/redis:\/\/\([^:]*\):.*/\1/p')
    REDIS_PORT=$(echo $REDIS_URL | sed -n 's/redis:\/\/[^:]*:\([0-9]*\).*/\1/p')
    
    if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ]; then
        log_warning "Could not parse Redis connection details, skipping wait"
        return 0
    fi
    
    # Wait for Redis connection
    for i in {1..15}; do
        if nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; then
            log_success "Redis is ready!"
            return 0
        fi
        log_info "Redis not ready, waiting... ($i/15)"
        sleep 2
    done
    
    log_error "Redis did not become ready in time"
    exit 1
}

# Check translations (Fluent format - no compilation needed)
check_translations() {
    log_info "Checking translations..."
    
    if [ -d "locales" ]; then
        # Count .ftl files
        ftl_count=$(find locales -name "*.ftl" | wc -l)
        log_success "Found $ftl_count Fluent translation files"
    else
        log_warning "No locales directory found"
    fi
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Check if we have migration scripts
    if [ -d "src/infrastructure/database/migrations" ]; then
        log_info "Running custom database migrations..."
        python -c "
import asyncio
from src.infrastructure.database.migrations.migration_manager import MigrationManager

async def run_migrations():
    try:
        manager = MigrationManager()
        await manager.run_migrations()
        print('Database migrations completed successfully')
        return True
    except Exception as e:
        print(f'Database migrations failed: {e}')
        return False

if not asyncio.run(run_migrations()):
    exit(1)
"
        if [ $? -eq 0 ]; then
            log_success "Database migrations completed successfully"
        else
            log_error "Database migrations failed"
            exit 1
        fi
    else
        log_warning "No migration scripts found, skipping migrations"
    fi
}

# Initialize data directories
init_directories() {
    log_info "Initializing data directories..."
    
    # Create required directories only if they don't exist and we have permission
    if [ -w "/app/data" ]; then
        mkdir -p /app/data/backups 2>/dev/null || log_warning "Could not create /app/data/backups"
    fi
    
    if [ -w "/app" ]; then
        mkdir -p /app/logs 2>/dev/null || log_warning "Could not create /app/logs"
        mkdir -p /app/static 2>/dev/null || log_warning "Could not create /app/static" 
        mkdir -p /app/templates 2>/dev/null || log_warning "Could not create /app/templates"
    fi
    
    log_success "Data directories checked"
}

# Create default configuration files
create_default_configs() {
    log_info "Creating default configuration files..."
    
    # Create products.json if it doesn't exist
    if [ ! -f "/app/data/products.json" ]; then
        cat > /app/data/products.json << 'EOF'
{
  "categories": [
    {
      "id": "software",
      "name": "Software Licenses",
      "description": "Premium software licenses and tools",
      "emoji": "💻"
    },
    {
      "id": "gaming",
      "name": "Gaming",
      "description": "Game keys and gaming subscriptions", 
      "emoji": "🎮"
    },
    {
      "id": "subscription",
      "name": "Subscriptions",
      "description": "Monthly and yearly subscriptions",
      "emoji": "📱"
    }
  ],
  "products": [
    {
      "id": "premium_1month",
      "name": "Premium Access - 1 Month",
      "description": "One month of premium access with all features",
      "category_id": "subscription",
      "price": 9.99,
      "currency": "USD",
      "duration_days": 30,
      "is_active": true,
      "stock": 1000,
      "delivery_type": "automatic",
      "metadata": {
        "features": ["Feature 1", "Feature 2", "Feature 3"],
        "delivery_template": "Thank you for your purchase! Your premium access is now active."
      }
    }
  ]
}
EOF
        log_success "Created default products.json"
    fi
}

# Start the appropriate service
start_service() {
    local service_type="${1:-${SERVICE_TYPE:-bot}}"
    
    log_info "Starting service: $service_type"
    
    case "$service_type" in
        "bot")
            log_info "Starting Telegram Bot..."
            exec python -m src.main
            ;;
        "admin")
            log_info "Starting Admin Panel..."
            exec python -m src.presentation.web.admin_panel
            ;;
        "scheduler")
            log_info "Starting Task Scheduler..."
            exec python -m src.infrastructure.background_tasks.scheduler
            ;;
        "worker")
            log_info "Starting Background Worker..."
            exec python -m src.infrastructure.background_tasks.worker
            ;;
        "migration")
            log_info "Running migrations only..."
            run_migrations
            log_success "Migrations completed, exiting"
            exit 0
            ;;
        *)
            log_error "Unknown service type: $service_type"
            log_info "Available service types: bot, admin, scheduler, worker, migration"
            exit 1
            ;;
    esac
}

# Main startup sequence
main() {
    log_info "=== Digital Store Bot v2 Startup ==="
    log_info "Service Type: ${SERVICE_TYPE:-bot}"
    log_info "Environment: ${ENVIRONMENT:-production}"
    
    # Initialize directories
    init_directories
    
    # Wait for dependencies (except for migration-only runs)
    if [ "${SERVICE_TYPE:-bot}" != "migration" ]; then
        wait_for_database
        wait_for_redis
    else
        wait_for_database
    fi
    
    # Check translations
    check_translations
    
    # Run database migrations
    run_migrations
    
    # Create default configs
    create_default_configs
    
    # Start the service
    start_service "$@"
}

# Handle signals gracefully
cleanup() {
    log_info "Received shutdown signal, cleaning up..."
    # Add any cleanup tasks here
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start the application
main "$@"