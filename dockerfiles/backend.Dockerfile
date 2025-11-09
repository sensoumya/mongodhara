# Use official Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for production
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first (for better Docker layer caching)
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend/ .

# Set Python path for proper module imports
ENV PYTHONPATH=/app

# Set default environment variables (can be overridden at runtime)
ENV MONGO_URI=mongodb://localhost:27017
ENV BASE_PATH=""
ENV LOG_LEVEL=INFO
ENV ENVIRONMENT=production

# Expose port
EXPOSE 8000

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Run with Gunicorn using Uvicorn workers for production
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
