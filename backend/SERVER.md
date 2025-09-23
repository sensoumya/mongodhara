# MongoDB Backend Server

This backend server can be run in two modes:

## Development Mode (with hot reloading)

```bash
cd backend
python main.py
```

## Production Mode (with Gunicorn + Uvicorn workers)

### Option 1: Using the run script

```bash
cd backend
./run_server.sh
```

### Option 2: Direct Gunicorn command

```bash
cd backend
gunicorn -c gunicorn.conf.py main:app
```

### Option 3: Custom Gunicorn configuration

```bash
cd backend
gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## Configuration

The Gunicorn configuration is defined in `gunicorn.conf.py` with the following key settings:

- **Workers**: `CPU_COUNT * 2 + 1` (automatically calculated)
- **Worker Class**: `uvicorn.workers.UvicornWorker` (for ASGI compatibility)
- **Binding**: `0.0.0.0:8000`
- **Logging**: Access and error logs to stdout/stderr
- **Timeouts**: 30 seconds
- **Max Requests**: 1000 per worker (with jitter for graceful recycling)

## Environment Variables

Make sure to set up your `.env` file with the required MongoDB connection settings. The application will automatically load these when starting.

## Health Check

The server will be available at:

- Health check: `http://localhost:8000/`
- API documentation: `http://localhost:8000/docs`
