# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY alembic.ini ./
COPY alembic/ ./alembic/
COPY app/ ./app/
COPY rulesets/ ./rulesets/
COPY scripts/ ./scripts/

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port (configurable via PORT env var, default 8000)
EXPOSE 8000

# Health check uses PORT env var
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; import httpx; httpx.get(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/api/v1/health')" || exit 1

# Run the application - use shell form to expand PORT env var
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
