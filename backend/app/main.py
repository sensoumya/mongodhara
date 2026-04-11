# SPDX-License-Identifier: MIT
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.v1.routes import (
    collection,
    database,
    document,
    gridfs,
    index,
    permission,
)
from app.core.config import (
    BASE_PATH,
)
from app.core.exceptions import InvalidOpaqueIDError
from app.core.middleware import (
    AccessLogMiddleware,
    OpaqueIDDecodingMiddleware,
    PathDecodingMiddleware,
)

# Application metadata
APP_VERSION = "2.2"


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    # Build description based on authz configuration
    base_description = """A comprehensive MongoDB management REST API"""
        
    app = FastAPI(
        title="MongoDB Management API",
        description=base_description,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        root_path=BASE_PATH,
    )
    
    setup_middleware(app)
    setup_routes(app)
    setup_openapi_security(app)
    setup_exception_handlers(app)
    
    return app


def setup_openapi_security(app: FastAPI) -> None:
    """Configure OpenAPI security schemes for authentication headers."""
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Add servers section for reverse proxy support
        if BASE_PATH:
            openapi_schema["servers"] = [
                {"url": BASE_PATH}
            ]
        else:
            openapi_schema["servers"] = [
                {"url": "/"}
            ]
                
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi


def setup_middleware(app: FastAPI) -> None:
    """Configure application middleware.
    
    Middleware executes from OUTERMOST to INNERMOST on requests.
    Added first = OUTERMOST (runs first), Added last = INNERMOST (runs closest to routes)
    
    Execution order (request flow):
    1. AccessLogMiddleware -> logs original encrypted path
    2. PathDecodingMiddleware -> decodes base64 paths  
    3. OpaqueIDDecodingMiddleware -> decodes opaque IDs in paths
    4. CORSMiddleware -> handles CORS with fully decoded paths
    5. Routes
    """
    
    # CORS middleware (added first = runs closest to routes, sees fully decoded paths)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Opaque ID decoding middleware (added second = runs after PathDecoding, before CORS)
    app.add_middleware(OpaqueIDDecodingMiddleware)
    
    # Path decoding middleware (added third = runs after AccessLog, before OpaqueID)
    app.add_middleware(PathDecodingMiddleware)
    
    # Access logging middleware (added last = OUTERMOST, runs first, logs original path)
    app.add_middleware(AccessLogMiddleware)


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""
    
    @app.exception_handler(InvalidOpaqueIDError)
    async def invalid_opaque_id_handler(request, exc: InvalidOpaqueIDError):
        """Handle invalid opaque ID errors with 400 Bad Request."""
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid database or collection identifier"}
        )


def setup_routes(app: FastAPI) -> None:
    """Configure application routes."""
    
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint for monitoring and load balancers."""
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "MongoDB Management API",
                "version": APP_VERSION
            }
        )
        
    app.include_router(database.router, prefix="/v1")
    app.include_router(collection.router, prefix="/v1")
    app.include_router(document.router, prefix="/v1")
    app.include_router(gridfs.router, prefix="/v1")
    app.include_router(index.router, prefix="/v1")
    # Only include permission routes when authorization is enabled
    # if ENABLE_AUTHZ:
    app.include_router(permission.router, prefix="/v1")


app = create_app()

if __name__ == "__main__":
    import os

    import uvicorn
    
    # Get log level from environment
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    # Disable uvicorn access logs (we use AccessLogMiddleware instead)
    # Create custom log config to suppress uvicorn.access logger
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn.access"]["handlers"] = []  # Disable access logs
    
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["app"],
        reload_excludes=["__pycache__", "*.pyc", "*.pyo"],
        log_level=log_level,
        log_config=log_config
    )
