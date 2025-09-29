# Use official Python slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend/ .

# Expose port
EXPOSE 8000

# Create a non-root user and switch to it
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# Run with Gunicorn using Uvicorn workers for production
CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:app"]
