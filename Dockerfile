# Multi-stage Dockerfile for DeltaCrown
#
# Implements:
#     - Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#containerization
#     - Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md#deployment

# =============================================================================
# Stage 1: Base
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (includes Cairo libs for reportlab/CairoSVG)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    pkg-config \
    libcairo2-dev \
    libgirepository1.0-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 deltacrown

WORKDIR /app

# =============================================================================
# Stage 2: Dependencies
# =============================================================================
FROM base as dependencies

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 3: Development
# =============================================================================
FROM dependencies as development

# Install development dependencies
RUN pip install --no-cache-dir \
    ipython \
    django-debug-toolbar \
    pytest-django \
    pytest-asyncio \
    pytest-cov

# Copy application code
COPY --chown=deltacrown:deltacrown . .

# Switch to non-root user
USER deltacrown

# Expose port
EXPOSE 8000

# Development server with hot-reload
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# =============================================================================
# Stage 4: Production
# =============================================================================
FROM dependencies as production

# Copy application code
COPY --chown=deltacrown:deltacrown . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Switch to non-root user
USER deltacrown

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz').read()"

# Run with gunicorn + daphne
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "deltacrown.asgi:application"]
