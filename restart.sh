#!/bin/bash

# =============================================================================
# Digital Store Bot v2 - Complete Restart Script
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

log_info "=== Digital Store Bot v2 Complete Restart ==="

# Step 1: Stop containers and remove volumes
log_info "Stopping containers and removing volumes..."
docker compose down -v
if [ $? -eq 0 ]; then
    log_success "Containers stopped and volumes removed"
else
    log_error "Failed to stop containers"
    exit 1
fi

# Step 2: Rebuild containers without cache
log_info "Rebuilding containers without cache..."
docker compose build --no-cache
if [ $? -eq 0 ]; then
    log_success "Containers rebuilt successfully"
else
    log_error "Failed to rebuild containers"
    exit 1
fi

# Step 3: Start containers
log_info "Starting containers..."
docker compose up