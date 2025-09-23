#!/bin/bash
# run_server.sh - Script to run the backend with Gunicorn

# Set environment variables if .env file exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Change to backend directory if not already there
if [ ! -f "main.py" ]; then
    cd backend
fi

echo "Starting Mongodhara backend with Gunicorn + Uvicorn workers..."

# Get CPU count in a cross-platform way
if command -v nproc >/dev/null 2>&1; then
    # Linux
    CPU_COUNT=$(nproc)
elif command -v sysctl >/dev/null 2>&1; then
    # macOS
    CPU_COUNT=$(sysctl -n hw.ncpu)
else
    # Fallback
    CPU_COUNT=4
fi

WORKERS=$((CPU_COUNT * 2 + 1))
echo "CPU cores: $CPU_COUNT"
echo "Workers: $WORKERS"
echo "Binding to: 0.0.0.0:8000"

# Run with Gunicorn using the configuration file
exec gunicorn -c gunicorn.conf.py main:app