# Digital Store Bot v2 - Deployment Guide

This guide provides comprehensive instructions for deploying Digital Store Bot v2 in production using Docker Compose.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Environment Configuration](#environment-configuration)
4. [Docker Compose Setup](#docker-compose-setup)
5. [SSL Configuration](#ssl-configuration)
6. [Database Setup](#database-setup)
7. [Payment Gateway Configuration](#payment-gateway-configuration)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Recovery](#backup--recovery)
10. [Troubleshooting](#troubleshooting)
11. [Production Optimization](#production-optimization)

## 🔧 Prerequisites

### System Requirements
- **Operating System**: Linux (Ubuntu 20.04+ recommended)
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Storage**: Minimum 10GB free space
- **Network**: Public IP with open ports 80, 443

### Software Dependencies
- **Docker**: 20.10.0+
- **Docker Compose**: 2.0.0+
- **Git**: 2.30.0+

### Install Dependencies

#### Ubuntu/Debian
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo apt install git -y
```

#### CentOS/RHEL
```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo yum install git -y
```

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/your-org/digital-store-bot-v2.git
cd digital-store-bot-v2
```

### 2. Copy Configuration Templates
```bash
cp .env.example .env
cp data/products.example.json data/products.json
```

### 3. Configure Environment
```bash
nano .env  # Edit with your settings
```

### 4. Deploy
```bash
# Build and start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f bot
```

## ⚙️ Environment Configuration

### Required Environment Variables

Edit `.env` file with your configuration:

```bash
# =============================================================================
# CORE BOT CONFIGURATION
# =============================================================================

# Telegram Bot Token (from @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Bot Domain (for webhooks, without protocol)
BOT_DOMAIN=yourdomain.com

# Admin Telegram IDs (comma-separated)
ADMIN_IDS=123456789,987654321

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database URL (PostgreSQL for production)
DATABASE_URL=postgresql+asyncpg://botuser:secure_password@postgres:5432/digital_store_bot

# Redis URL (for caching and sessions)
REDIS_URL=redis://redis:6379/0

# =============================================================================
# PAYMENT GATEWAYS
# =============================================================================

# Telegram Stars
TELEGRAM_STARS_ENABLED=true

# Cryptomus
CRYPTOMUS_ENABLED=true
CRYPTOMUS_MERCHANT_ID=your_merchant_id
CRYPTOMUS_API_KEY=your_api_key
CRYPTOMUS_WEBHOOK_SECRET=your_webhook_secret

# =============================================================================
# SHOP CONFIGURATION
# =============================================================================

# Default currency
DEFAULT_CURRENCY=USD

# Trial system
TRIAL_DURATION_DAYS=3
REFERRAL_TRIAL_EXTENSION_DAYS=2

# Referral system
REFERRAL_LEVEL1_PERCENT=10
REFERRAL_LEVEL2_PERCENT=5

# =============================================================================
# SSL CONFIGURATION (Let's Encrypt)
# =============================================================================

# Email for SSL certificates
LETSENCRYPT_EMAIL=admin@yourdomain.com

# =============================================================================
# LOGGING & MONITORING
# =============================================================================

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Sentry DSN (optional, for error tracking)
SENTRY_DSN=https://your-sentry-dsn

# =============================================================================
# SECURITY
# =============================================================================

# Secret key for JWT tokens
SECRET_KEY=your-very-secure-secret-key-here

# Admin panel credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_password

# =============================================================================
# NOTIFICATION SETTINGS
# =============================================================================

# Email notifications (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourdomain.com

# SMS notifications (optional)
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=+1234567890
```

## 🐳 Docker Compose Setup

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # =============================================================================
  # Reverse Proxy & SSL Termination
  # =============================================================================
  traefik:
    image: traefik:v3.0
    container_name: traefik
    restart: unless-stopped
    command:
      - "--api.dashboard=true"
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=${LETSENCRYPT_EMAIL}"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--global.sendanonymoususage=false"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_letsencrypt:/letsencrypt
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`traefik.${BOT_DOMAIN}`)"
      - "traefik.http.routers.dashboard.tls=true"
      - "traefik.http.routers.dashboard.tls.certresolver=letsencrypt"
      - "traefik.http.routers.dashboard.service=api@internal"
      - "traefik.http.routers.dashboard.middlewares=auth"
      - "traefik.http.middlewares.auth.basicauth.users=admin:$$2y$$10$$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi"

  # =============================================================================
  # Database Services
  # =============================================================================
  postgres:
    image: postgres:15-alpine
    container_name: postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: digital_store_bot
      POSTGRES_USER: botuser
      POSTGRES_PASSWORD: secure_password
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U botuser -d digital_store_bot"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "127.0.0.1:6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # =============================================================================
  # Application Services
  # =============================================================================
  bot:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    container_name: digital_store_bot
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://botuser:secure_password@postgres:5432/digital_store_bot
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./locales:/app/locales
      - ./templates:/app/templates
      - ./static:/app/static
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.bot.rule=Host(`${BOT_DOMAIN}`) && PathPrefix(`/webhook`)"
      - "traefik.http.routers.bot.tls=true"
      - "traefik.http.routers.bot.tls.certresolver=letsencrypt"
      - "traefik.http.services.bot.loadbalancer.server.port=8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  admin:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    container_name: admin_panel
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://botuser:secure_password@postgres:5432/digital_store_bot
      - REDIS_URL=redis://redis:6379/0
    command: ["python", "-m", "src.presentation.web.admin_panel"]
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./templates:/app/templates
      - ./static:/app/static
    depends_on:
      - postgres
      - redis
      - bot
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.admin.rule=Host(`admin.${BOT_DOMAIN}`)"
      - "traefik.http.routers.admin.tls=true"
      - "traefik.http.routers.admin.tls.certresolver=letsencrypt"
      - "traefik.http.services.admin.loadbalancer.server.port=8080"

  # =============================================================================
  # Background Services
  # =============================================================================
  scheduler:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    container_name: task_scheduler
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://botuser:secure_password@postgres:5432/digital_store_bot
      - REDIS_URL=redis://redis:6379/0
    command: ["python", "-m", "src.infrastructure.background_tasks.scheduler"]
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis

  # =============================================================================
  # Monitoring Services (Optional)
  # =============================================================================
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.prometheus.rule=Host(`metrics.${BOT_DOMAIN}`)"
      - "traefik.http.routers.prometheus.tls=true"
      - "traefik.http.routers.prometheus.tls.certresolver=letsencrypt"
      - "traefik.http.services.prometheus.loadbalancer.server.port=9090"

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.grafana.rule=Host(`grafana.${BOT_DOMAIN}`)"
      - "traefik.http.routers.grafana.tls=true"
      - "traefik.http.routers.grafana.tls.certresolver=letsencrypt"
      - "traefik.http.services.grafana.loadbalancer.server.port=3000"

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  traefik_letsencrypt:
    driver: local
  prometheus_data:
    driver: local
  grafana_data:
    driver: local

networks:
  default:
    name: digital_store_network
```

## 🐳 Dockerfile

Create optimized `Dockerfile`:

```dockerfile
# =============================================================================
# Multi-stage Dockerfile for Digital Store Bot v2
# =============================================================================

# Build stage
FROM python:3.12-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gettext \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.1

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy dependency files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --only=main && rm -rf $POETRY_CACHE_DIR

# =============================================================================
# Production stage
# =============================================================================
FROM python:3.12-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gettext \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r botuser \
    && useradd -r -g botuser botuser

# Copy virtual environment from builder stage
ENV VIRTUAL_ENV=/app/.venv
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=botuser:botuser . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/static /app/templates && \
    chown -R botuser:botuser /app

# Compile translations
RUN find locales -name "*.po" -exec msgfmt {} -o {}.mo \; || true

# Health check script
COPY --chown=botuser:botuser scripts/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Switch to non-root user
USER botuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Default command
CMD ["python", "-m", "src.main"]

# =============================================================================
# Development stage
# =============================================================================
FROM builder as development

# Install development dependencies
RUN poetry install && rm -rf $POETRY_CACHE_DIR

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/data /app/logs /app/static /app/templates

# Development command
CMD ["python", "-m", "src.main", "--dev"]
```

## 📂 Directory Structure

After deployment, your directory structure should look like:

```
digital-store-bot-v2/
├── .env                     # Environment configuration
├── .env.example            # Environment template
├── docker-compose.yml      # Main orchestration file
├── Dockerfile              # Application container
├── DEPLOYMENT_GUIDE.md     # This guide
├── data/                   # Persistent data
│   ├── products.json       # Product catalog
│   └── database.db        # SQLite (development)
├── logs/                   # Application logs
│   ├── bot.log
│   ├── admin.log
│   └── scheduler.log
├── locales/                # Translation files
│   ├── en/
│   ├── ru/
│   └── zh/
├── monitoring/             # Monitoring configuration
│   ├── prometheus.yml
│   └── grafana/
├── scripts/                # Deployment scripts
│   ├── install.sh
│   ├── backup.sh
│   ├── init-db.sql
│   └── healthcheck.sh
├── static/                 # Static web assets
├── templates/              # Web templates
└── src/                    # Application source code
```

## 🔒 SSL Configuration

### Automatic SSL with Let's Encrypt

The deployment automatically configures SSL certificates using Traefik and Let's Encrypt:

1. **Update DNS**: Point your domain to your server's IP
2. **Configure domain**: Set `BOT_DOMAIN` in `.env`
3. **Set email**: Set `LETSENCRYPT_EMAIL` in `.env`
4. **Deploy**: Certificates are automatically issued

### Manual SSL Certificate

If you prefer custom certificates:

```yaml
# In docker-compose.yml, replace letsencrypt with:
volumes:
  - ./ssl/cert.pem:/ssl/cert.pem:ro
  - ./ssl/key.pem:/ssl/key.pem:ro

# Update Traefik configuration
command:
  - "--entrypoints.websecure.address=:443"
  - "--providers.file.filename=/ssl/traefik-tls.yml"
```

## 🗄️ Database Setup

### PostgreSQL (Production)

Default configuration uses PostgreSQL for production:

```bash
# Create database backup
docker-compose exec postgres pg_dump -U botuser digital_store_bot > backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U botuser -d digital_store_bot < backup.sql

# Access database
docker-compose exec postgres psql -U botuser -d digital_store_bot
```

### Database Migrations

```bash
# Run migrations
docker-compose exec bot python -m alembic upgrade head

# Create new migration
docker-compose exec bot python -m alembic revision --autogenerate -m "description"

# Rollback migration
docker-compose exec bot python -m alembic downgrade -1
```

## 💳 Payment Gateway Configuration

### Telegram Stars

```bash
# In .env file:
TELEGRAM_STARS_ENABLED=true
```

### Cryptomus

```bash
# In .env file:
CRYPTOMUS_ENABLED=true
CRYPTOMUS_MERCHANT_ID=your_merchant_id
CRYPTOMUS_API_KEY=your_api_key
CRYPTOMUS_WEBHOOK_SECRET=your_webhook_secret
```

## 📊 Monitoring & Logging

### Application Logs

```bash
# View real-time logs
docker-compose logs -f bot

# View specific service logs
docker-compose logs -f admin
docker-compose logs -f scheduler

# View all logs
docker-compose logs --tail=100
```

### Prometheus Metrics

Access metrics at: `https://metrics.yourdomain.com`

### Grafana Dashboards

Access dashboards at: `https://grafana.yourdomain.com`
- Default login: admin/admin123

## 💾 Backup & Recovery

### Automated Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U botuser digital_store_bot | gzip > $BACKUP_DIR/database_$DATE.sql.gz

# Backup application data
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz .env docker-compose.yml

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

### Restore Procedure

```bash
# Stop services
docker-compose down

# Restore database
gunzip -c backup/database_20240101_120000.sql.gz | docker-compose exec -T postgres psql -U botuser -d digital_store_bot

# Restore data
tar -xzf backup/data_20240101_120000.tar.gz

# Start services
docker-compose up -d
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. SSL Certificate Issues
```bash
# Check certificate status
docker-compose logs traefik | grep -i certificate

# Force certificate renewal
docker-compose restart traefik
```

#### 2. Database Connection Issues
```bash
# Check database health
docker-compose exec postgres pg_isready -U botuser

# Reset database connection
docker-compose restart bot
```

#### 3. Bot Not Responding
```bash
# Check bot logs
docker-compose logs bot | tail -50

# Restart bot service
docker-compose restart bot

# Check webhook status
curl -X GET "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

#### 4. Memory Issues
```bash
# Check system resources
docker stats

# Restart all services
docker-compose restart
```

### Log Analysis

```bash
# Search for errors
docker-compose logs bot | grep -i error

# Monitor real-time errors
docker-compose logs -f bot | grep -i error

# Check specific time range
docker-compose logs --since="2024-01-01T10:00:00" --until="2024-01-01T11:00:00" bot
```

## 🚀 Production Optimization

### Performance Tuning

#### 1. PostgreSQL Optimization

Create `postgres.conf`:

```ini
# PostgreSQL Performance Tuning
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

#### 2. Redis Optimization

```yaml
# In docker-compose.yml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru --save 900 1
```

#### 3. Application Scaling

```yaml
# Scale bot instances
bot:
  deploy:
    replicas: 3
    resources:
      limits:
        memory: 512M
      reservations:
        memory: 256M
```

### Security Hardening

#### 1. Firewall Configuration

```bash
# Ubuntu UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### 2. Docker Security

```yaml
# Add to docker-compose.yml
security_opt:
  - no-new-privileges:true
read_only: true
tmpfs:
  - /tmp
```

#### 3. Environment Security

```bash
# Secure .env file
chmod 600 .env
chown root:root .env
```

## 📋 Maintenance

### Regular Tasks

```bash
# Weekly maintenance script
#!/bin/bash

# Update containers
docker-compose pull
docker-compose up -d

# Clean unused images
docker image prune -f

# Backup data
./scripts/backup.sh

# Check disk space
df -h

# Check logs
docker-compose logs --tail=100 | grep -i error
```

### Updates

```bash
# Update to latest version
git pull origin main
docker-compose build --no-cache
docker-compose up -d
```

## 🎯 Quick Commands Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart bot

# View logs
docker-compose logs -f bot

# Check status
docker-compose ps

# Execute commands in container
docker-compose exec bot python -c "print('Hello')"

# Scale services
docker-compose up -d --scale bot=3

# Update and restart
docker-compose pull && docker-compose up -d

# Full cleanup
docker-compose down -v && docker system prune -af
```

---

## 🏁 Conclusion

This deployment guide provides a production-ready setup for Digital Store Bot v2 with:

- ✅ **Automatic SSL certificates**
- ✅ **Database clustering**
- ✅ **Horizontal scaling**
- ✅ **Monitoring & alerting**
- ✅ **Automated backups**
- ✅ **Security hardening**
- ✅ **Zero-downtime deployments**

For additional support, check the troubleshooting section or contact the development team.

**Happy Deploying! 🚀**