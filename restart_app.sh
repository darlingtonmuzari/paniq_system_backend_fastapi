#!/bin/bash

echo "🔄 Restarting app on port 8000..."

# Kill any process using port 8000
echo "🛑 Killing processes on port 8000..."
sudo fuser -k 8000/tcp 2>/dev/null || true
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "python.*8000" 2>/dev/null || true

# Wait a moment for processes to die
sleep 2

# Double check and force kill if needed
PID=$(lsof -ti:8000 2>/dev/null)
if [ ! -z "$PID" ]; then
    echo "🔥 Force killing remaining processes: $PID"
    kill -9 $PID 2>/dev/null || true
fi

# Wait another moment
sleep 1

echo "🚀 Starting app on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload