#!/bin/bash

# Development startup script for Panic System Platform
# This script starts the supporting services in Docker and runs FastAPI locally

set -e

echo "🚀 Starting Panic System Development Environment"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Stop any existing API container
print_status "Stopping existing API container if running..."
docker stop panic-system-api 2>/dev/null || true
docker rm panic-system-api 2>/dev/null || true

# Start supporting services (without API)
print_status "Starting supporting services (PostgreSQL, Redis, Celery, etc.)..."
docker compose up -d postgres redis celery celery-beat prometheus grafana

# Wait for services to be healthy
print_status "Waiting for services to be ready..."
sleep 10

# Check service health
print_status "Checking service health..."

# Check PostgreSQL
if docker exec panic-system-db pg_isready -U postgres -d panic_system > /dev/null 2>&1; then
    print_success "PostgreSQL is ready"
else
    print_error "PostgreSQL is not ready"
    exit 1
fi

# Check Redis
if docker exec panic-system-redis redis-cli -a redis_password ping > /dev/null 2>&1; then
    print_success "Redis is ready"
else
    print_error "Redis is not ready"
    exit 1
fi

# Copy development environment
print_status "Setting up development environment..."
cp .env.development .env

# Create necessary directories
mkdir -p logs uploads

print_success "Supporting services are ready!"
echo ""
echo "📋 Service Status:"
echo "  🐘 PostgreSQL: http://localhost:5433"
echo "  🔴 Redis: localhost:6380"
echo "  📊 Grafana: http://localhost:3000 (admin/admin123)"
echo "  📈 Prometheus: http://localhost:9091"
echo ""
echo "🔧 Development Commands:"
echo "  Start API: python -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload"
echo "  Run tests: python -m pytest"
echo "  Format code: python -m black app/"
echo ""
echo "🛑 To stop services: docker compose down"
echo ""
print_warning "Remember to install Python dependencies if not already done:"
echo "  pip install -r requirements.txt"
echo ""
print_success "Development environment is ready! 🎉"