"""Main FastAPI application for EduSched.

Provides REST API for schedule generation, management, and export.
"""

try:
    from contextlib import asynccontextmanager
    import logging
    from typing import List

    from fastapi import FastAPI, HTTPException, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from fastapi.responses import JSONResponse

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from edusched.api import __version__

# Only create app if FastAPI is available
if FASTAPI_AVAILABLE:
    from edusched.api.dependencies import check_rate_limit
    from edusched.api.routes import files, schedules

    logger = logging.getLogger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle."""
        # Startup
        logger.info("EduSched API starting up...")
        logger.info("Version: %s", __version__)

        # Initialize any necessary resources
        # For example: database connections, cache, etc.

        yield

        # Shutdown
        logger.info("EduSched API shutting down...")

    # Create FastAPI app
    app = FastAPI(
        title="EduSched API",
        description="REST API for educational institution scheduling",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Add trusted host middleware for security
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.example.com"],
    )

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Error",
                "message": exc.detail,
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": str(exc),
                "status_code": 500,
            },
        )

    # Root endpoints
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "EduSched API",
            "version": __version__,
            "description": "Educational scheduling system REST API",
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": __version__,
        }

    @app.get("/version")
    async def get_version():
        """Get API version information."""
        return {
            "version": __version__,
            "api_version": "v1",
        }

    # Include routers
    from edusched.api.routes import conflicts, optimization

    app.include_router(
        schedules.router,
        prefix="/api/v1/schedules",
        tags=["schedules"],
    )

    app.include_router(
        conflicts.router,
        prefix="/api/v1/conflicts",
        tags=["conflicts"],
    )
    app.include_router(
        optimization.router,
        prefix="/api/v1/optimization",
        tags=["optimization"],
    )
    app.include_router(
        files.router,
        prefix="/api/v1/files",
        tags=["files"],
    )

    # Add WebSocket endpoint
    from fastapi import WebSocket

    from edusched.api.websocket import websocket_endpoint

    @app.websocket("/ws")
    async def websocket_route(
        websocket: WebSocket,
        user_id: str,
        schedule_id: str = None,
    ):
        """WebSocket endpoint for real-time updates."""
        await websocket_endpoint(websocket, user_id, schedule_id)

    # Rate limiting middleware
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        """Apply rate limiting to all requests."""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit (skip for health checks)
        if not request.url.path.startswith("/health"):
            await check_rate_limit(client_ip)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = "100"
        response.headers["X-RateLimit-Remaining"] = "99"

        return response

    # Security middleware
    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        """Add security headers and enforce request body size limits."""
        max_body_bytes = int(
            request.headers.get("x-max-body-bytes", "0")
            or request.app.state.__dict__.get("max_body_bytes", 0)
            or 2_000_000
        )

        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > max_body_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Payload Too Large",
                            "message": f"Request body exceeds limit of {max_body_bytes} bytes",
                            "status_code": 413,
                        },
                    )
            except ValueError:
                pass

        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")

        if request.url.scheme in {"https", "wss"}:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response

else:
    # Create a dummy app for type checking
    app = None


# Development server startup
def run_dev_server():
    """Run the development server."""
    if not FASTAPI_AVAILABLE:
        logging.getLogger(__name__).error(
            "FastAPI is not installed. Install with: pip install fastapi uvicorn"
        )
        return
 
    import uvicorn
 
    logger = logging.getLogger(__name__)
    logger.info("%s", "=" * 50)
    logger.info("EduSched API Development Server")
    logger.info("%s", "=" * 50)
    logger.info("Version: %s", __version__)
    logger.info("API Documentation: http://localhost:8000/docs")
    logger.info("ReDoc Documentation: http://localhost:8000/redoc")
    logger.info("Health Check: http://localhost:8000/health")
    logger.info("%s", "=" * 50)
 
    uvicorn.run(
        "edusched.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    run_dev_server()
