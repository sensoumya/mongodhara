#!/bin/bash

# MongoDB Backend Server - Local Development Runner

set -e

echo "🚀 Starting MongoDB Backend Server"
echo " API docs: http://localhost:8000/docs"
echo ""

# Run with hot reload
python app/main.py