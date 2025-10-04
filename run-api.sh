#!/bin/bash

# Quick API startup script
echo "🚀 Starting FastAPI Development Server..."
echo "========================================"

# Ensure we're using the development environment
if [ ! -f .env ]; then
    echo "📋 Copying development environment..."
    cp .env.development .env
fi

# Create directories if they don't exist
mkdir -p logs uploads

# Start the API with hot reload
echo "🔥 Starting with hot reload on http://localhost:8010"
echo "📚 API docs available at http://localhost:8010/docs"
echo "🛑 Press Ctrl+C to stop"
echo ""

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload