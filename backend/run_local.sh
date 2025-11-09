#!/bin/bash

# MongoDB Backend Server - Local Development Runner

set -e

echo "🚀 Starting MongoDB Backend Server"
echo " API docs: http://localhost:8000/docs"
echo ""

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements if not already installed
if ! pip show -q fastapi; then
    echo "Installing requirements..."
    pip install -r requirements.txt
fi

# Run with hot reload
echo "Starting server..."
python app/main.py