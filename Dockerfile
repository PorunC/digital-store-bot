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
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN --mount=type=cache,target=/tmp/poetry_cache \
    poetry install --only=main --no-root && \
    rm -rf /tmp/poetry_cache

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

# Copy virtual environment from builder stage
ENV VIRTUAL_ENV=/app/.venv
COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=botuser:botuser src/ src/
COPY --chown=botuser:botuser config/ config/
COPY --chown=botuser:botuser data/ data/
COPY --chown=botuser:botuser pyproject.toml pytest.ini ./
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

# Default command
CMD ["bot"]

# =============================================================================
# Development stage
# =============================================================================
FROM builder AS development

# Install development dependencies
RUN --mount=type=cache,target=$POETRY_CACHE_DIR \
    poetry install && \
    rm -rf $POETRY_CACHE_DIR

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