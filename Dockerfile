# Multi-stage build for production optimization
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    libgeos-dev \
    libproj-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install --user -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    libgeos-c1t64 \
    libproj25 \
    libgdal36 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /home/app/.local

# Make sure scripts in .local are usable
ENV PATH=/home/app/.local/bin:$PATH

# Copy application code
COPY . .

# Create directories for logs and uploads
RUN mkdir -p /app/logs /app/uploads

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 app \
    && chown -R app:app /app \
    && chown -R app:app /home/app/.local
USER app

# Expose ports
EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Development stage
FROM production as development

# Install development dependencies as app user
USER app
RUN pip install --user --no-cache-dir pytest pytest-asyncio pytest-cov black isort flake8

# Override CMD for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]