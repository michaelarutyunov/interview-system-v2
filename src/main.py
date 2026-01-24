"""
FastAPI application entry point.

Run with: uvicorn src.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.logging import configure_logging, get_logger
from src.persistence.database import init_database
from src.api.routes import health, sessions, synthetic
from src.api.routes.concepts import router as concepts_router
from src.api.exception_handlers import setup_exception_handlers

# Configure logging before anything else
configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    log.info(
        "application_starting",
        debug=settings.debug,
        database_path=str(settings.database_path),
    )

    # Initialize database
    await init_database()

    log.info("application_started")

    yield

    # Shutdown
    log.info("application_shutting_down")


# Create FastAPI application
app = FastAPI(
    title="Interview System v2",
    description="Adaptive interview system for qualitative consumer research",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# CORS middleware for development
if settings.debug:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Setup exception handlers
setup_exception_handlers(app)

# Include routers
app.include_router(health.router, tags=["system"])
app.include_router(sessions.router)
app.include_router(synthetic.router)

# Register concepts router
app.include_router(concepts_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {"name": "Interview System v2", "version": "0.1.0", "status": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
