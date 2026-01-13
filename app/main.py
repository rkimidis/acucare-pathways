"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.init_db import init_db
from app.db.session import AsyncSessionLocal
from app.middleware.rbac import RBACMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    logger.info(f"Starting AcuCare Pathways API (env={settings.env})")

    if settings.init_db_on_startup and settings.is_dev:
        logger.info("Initializing database...")
        async with AsyncSessionLocal() as session:
            await init_db(session)

    yield

    # Shutdown
    logger.info("Shutting down AcuCare Pathways API")


# Create FastAPI application
app = FastAPI(
    title="AcuCare Pathways API",
    description="UK Private Psychiatric Clinic Platform (CQC-registered)",
    version="0.1.0",
    docs_url="/docs" if settings.is_dev else None,
    redoc_url="/redoc" if settings.is_dev else None,
    openapi_url="/openapi.json" if settings.is_dev else None,
    lifespan=lifespan,
)

# Add RBAC middleware
app.add_middleware(RBACMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, enabled=settings.rate_limit_enabled)

# CORS middleware (configure appropriately for production)
if settings.is_dev:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions."""
    logger.exception(f"Unhandled exception: {exc}")

    # Don't expose internal errors in production
    if settings.is_prod:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Root endpoint redirect to docs."""
    return {
        "service": "AcuCare Pathways API",
        "version": "0.1.0",
        "docs": "/docs" if settings.is_dev else "Disabled in production",
    }
