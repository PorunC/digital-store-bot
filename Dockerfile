# =============================================================================
# Multi-stage Dockerfile for Digital Store Bot v2
# =============================================================================

# Build stage
FROM python:3.12-slim AS builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    gettext \
    git \
    pkg-config \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Configure Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_INSTALLER_PARALLEL=true

# Copy dependency files
WORKDIR /app
COPY pyproject.toml ./

# Generate lock file and install dependencies
RUN --mount=type=cache,target=/tmp/poetry_cache \
    poetry lock --no-update && \
    poetry install --only=main --no-root

# =============================================================================
# Production stage
# =============================================================================
FROM python:3.12-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gettext \
    libpq5 \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r botuser \
    && useradd -r -g botuser -d /app -s /bin/bash botuser

# Install Poetry and dependencies directly in production
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies globally (no virtual env)
RUN poetry config virtualenvs.create false && \
    poetry lock --no-update && \
    poetry install --only=main --no-root

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=botuser:botuser src/ src/
COPY --chown=botuser:botuser config/ config/
COPY --chown=botuser:botuser data/ data/
# pytest configuration is in pyproject.toml - no separate pytest.ini needed
COPY --chown=botuser:botuser .env.example ./

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/static /app/templates /app/locales && \
    chown -R botuser:botuser /app && \
    chmod -R 755 /app/data /app/logs

# Copy locales directory (Fluent format - no compilation needed)
COPY --chown=botuser:botuser locales/ locales/

# Copy scripts
COPY --chown=botuser:botuser scripts/ scripts/
RUN chmod +x scripts/*.sh

# Health check script
COPY --chown=botuser:botuser scripts/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Copy startup script
COPY --chown=botuser:botuser scripts/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Switch to non-root user
USER botuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Use startup script as entrypoint
ENTRYPOINT ["/usr/local/bin/start.sh"]

# No default command - use SERVICE_TYPE environment variable instead

# =============================================================================
# Development stage
# =============================================================================
FROM builder AS development

# Install development dependencies
RUN --mount=type=cache,target=/tmp/poetry_cache \
    poetry install

# Install additional development tools
RUN pip install --no-cache-dir \
    debugpy \
    ipython \
    rich

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/data /app/logs /app/static /app/templates /app/locales

# Make scripts executable
RUN find scripts -name "*.sh" -exec chmod +x {} \;

# Development user setup
RUN groupadd -r devuser && \
    useradd -r -g devuser -d /app -s /bin/bash devuser && \
    chown -R devuser:devuser /app

USER devuser

# Development command with auto-reload
CMD ["python", "-m", "src.main"]