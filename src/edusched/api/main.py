"""Main FastAPI application for EduSched.

Provides REST API for schedule generation, management, and export.
"""

try:
    from contextlib import asynccontextmanager
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
    from edusched.api.routes import schedules, bulk_import

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle."""
        # Startup
        print("🚀 EduSched API starting up...")
        print(f"Version: {__version__}")

        # Initialize any necessary resources
        # For example: database connections, cache, etc.

        yield

        # Shutdown
        print("🛑 EduSched API shutting down...")

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
    app.include_router(
        schedules.router,
        prefix="/api/v1/schedules",
        tags=["schedules"],
    )

    app.include_router(
        bulk_import.router,
        prefix="/api/v1",
        tags=["bulk_import"],
    )

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

else:
    # Create a dummy app for type checking
    app = None


# Development server startup
def run_dev_server():
    """Run the development server."""
    if not FASTAPI_AVAILABLE:
        print("❌ FastAPI is not installed. Install with: pip install fastapi uvicorn")
        return

    import uvicorn

    print("\n" + "="*50)
    print("EduSched API Development Server")
    print("="*50)
    print(f"Version: {__version__}")
    print("API Documentation: http://localhost:8000/docs")
    print("ReDoc Documentation: http://localhost:8000/redoc")
    print("Health Check: http://localhost:8000/health")
    print("="*50 + "\n")

    uvicorn.run(
        "edusched.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    run_dev_server()