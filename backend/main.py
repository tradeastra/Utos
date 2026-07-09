"""
Main application entry point for UTOS Trading Engine.

This module initializes the FastAPI application and sets up all
necessary components.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from core.config import settings
from core.logging import get_logger
from api.v1 import api_router
from core.exceptions import UTOSException


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting UTOS Trading Engine...")
    
    # Initialize core components
    # TODO: Initialize database
    # TODO: Initialize Redis
    # TODO: Initialize event bus
    # TODO: Initialize kernel context
    
    logger.info("UTOS Trading Engine started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down UTOS Trading Engine...")
    
    # Cleanup components
    # TODO: Close database connections
    # TODO: Close Redis connections
    # TODO: Close event bus
    
    logger.info("UTOS Trading Engine shut down successfully")


# Create FastAPI application
app = FastAPI(
    title="UTOS Trading Engine API",
    description="Unified Trading Operating System Trading Engine",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(UTOSException)
async def utos_exception_handler(request: Request, exc: UTOSException):
    """Handle UTOS exceptions."""
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": str(exc) if settings.DEBUG else None,
            }
        },
    )


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": "2026-07-09T00:00:00Z",
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "UTOS Trading Engine API",
        "version": "2.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )