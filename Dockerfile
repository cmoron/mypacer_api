# Multi-stage Dockerfile for mypacer_api
# - "base" target: installs dependencies
# - "prod" target: minimal production image (default)
# - "dev" target: hot-reload server for local development

# =============================================================================
# Base image with dependencies
# =============================================================================
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps first to leverage Docker cache
# curl is used for the healthcheck in the prod image
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Production image (default)
# =============================================================================
FROM base AS prod

# Add ARGs for user and group IDs to be passed during build
ARG HOST_UID=1000
ARG HOST_GID=1000

# Create a non-root user with specified UID and GID to match the host user
# This avoids permission errors on mounted volumes in development
# Use -o flag to allow non-unique GID/UID (safe in isolated Docker container)
# This handles cases where GID/UID already exists (e.g., macOS GID 20 = staff)
RUN groupadd -o -g $HOST_GID -r appuser && \
    useradd -o -u $HOST_UID -r -g appuser appuser

# Copy application code
COPY --chown=appuser:appuser mypacer_api/ ./mypacer_api/
# The db/init.sql is used by the postgres container, not the api one.
# Only copy what's necessary for the application to run.
# COPY --chown=appuser:appuser db/ ./db/ 
# COPY --chown=appuser:appuser run.sh ./run.sh

USER appuser

EXPOSE 8000

# Healthcheck uses curl, which was installed in the base image
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "mypacer_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Development image (inherits from prod)
# Overrides the CMD for hot-reloading.
# Source code is provided via a volume mount in docker-compose.dev.yml.
# =============================================================================
FROM prod AS dev

CMD ["uvicorn", "mypacer_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
