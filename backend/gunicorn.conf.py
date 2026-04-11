# SPDX-License-Identifier: MIT
# gunicorn.conf.py
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 4  # Fixed 4 workers for optimal performance with 100MB max files
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000  # 1000 concurrent connections per worker
threads = 2  # 2 threads per worker for I/O operations
max_requests = 2000  # Recycle worker after 2000 requests
max_requests_jitter = 200  # Add jitter to prevent thundering herd

# Timeouts
timeout = 120  # 2 minutes (optimized for 100MB uploads)
keepalive = 5  # Keep connections alive for 5 seconds

# Logging
# Disable uvicorn access logs (we handle them in AccessLogMiddleware)
accesslog = None  # Disable default access logs
errorlog = "-"  # Keep error logs
loglevel = os.getenv("LOG_LEVEL", "info").lower()
# access_log_format not needed since accesslog is disabled

# Process naming
proc_name = "mongodhara-backend"

# Server mechanics
daemon = False
# pidfile = "/tmp/gunicorn.pid"  # Not needed in Docker containers
user = None
group = None
tmp_upload_dir = None

# SSL (for production use)
# keyfile = None
# certfile = None

# Environment variables
raw_env = [
    f"PYTHONPATH={os.getcwd()}"
]

# Preload application
preload_app = True

# Worker lifecycle hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Mongodhara backend server...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Mongodhara backend server...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"Mongodhara backend server is ready. Listening on: {server.address}")

def worker_int(worker):
    """Called just after a worker has been exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")