# gunicorn.conf.py
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Timeouts
timeout = 30
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

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