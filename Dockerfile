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

# pip < 26.2.2 always trusts its vendored certifi, which still holds the
# compromised "emSign ECC Root CA - G3". Upgrade from a hash-pinned wheel
# before any other install (https://discuss.python.org/t/109576).
RUN pip install --no-cache-dir "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"

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
