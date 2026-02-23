"""
FastAPI application entry point.

Run with: uvicorn src.main:app --reload
"""

from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.core.config import settings
from src.core.logging import configure_logging, get_logger, bind_context, clear_context
from src.persistence.database import init_database
from src.api.routes import health, sessions, synthetic
from src.api.routes.concepts import router as concepts_router
from src.api.routes.simulation import router as simulation_router
from src.api.exception_handlers import setup_exception_handlers

# Configure logging before anything else
configure_logging()
log = get_logger(__name__)


# =============================================================================
# Correlation ID Middleware
# =============================================================================


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique correlation ID to each request.

    - Generates a UUID4 request_id for each incoming request
    - Binds it to structlog context for all logs in that request
    - Adds X-Request-ID header to responses

    This allows tracing all log entries for a specific request.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and add correlation ID."""
        # Generate or retrieve request ID
        request_id = str(uuid.uuid4())

        # Bind to structlog context for all subsequent logs
        bind_context(request_id=request_id)

        try:
            # Call next middleware/endpoint
            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response
        finally:
            # Clear context after request completes
            clear_context()


# =============================================================================
# LLM Provider Defaults (must match client.py)
# =============================================================================

# These are copied from src/llm/client.py to validate API keys at startup
# without importing the client module (avoiding circular imports).

EXTRACTION_DEFAULT_PROVIDER = "anthropic"
SCORING_DEFAULT_PROVIDER = "kimi"
GENERATION_DEFAULT_PROVIDER = "anthropic"


def validate_api_keys() -> list[str]:
    """
    Validate that required API keys are configured.

    Checks API keys for all configured LLM providers. If a provider is
    configured (either via default or environment override), its API key
    must be present.

    Returns:
        List of error messages (empty if all keys are valid)

    Raises:
        RuntimeError: If any required API key is missing
    """
    errors = []

    # Determine which providers are in use
    extraction_provider = settings.llm_extraction_provider or EXTRACTION_DEFAULT_PROVIDER
    scoring_provider = settings.llm_scoring_provider or SCORING_DEFAULT_PROVIDER
    generation_provider = settings.llm_generation_provider or GENERATION_DEFAULT_PROVIDER

    # Map providers to their API key attributes and env var names
    providers = {
        "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
        "kimi": ("kimi_api_key", "KIMI_API_KEY"),
        "deepseek": ("deepseek_api_key", "DEEPSEEK_API_KEY"),
    }

    # Check each provider in use
    for client_type, provider in [
        ("extraction", extraction_provider),
        ("scoring", scoring_provider),
        ("generation", generation_provider),
    ]:
        if provider not in providers:
            errors.append(
                f"Unknown LLM provider '{provider}' for {client_type}. "
                f"Supported providers: {', '.join(providers.keys())}"
            )
            continue

        attr_name, env_var = providers[provider]
        api_key = getattr(settings, attr_name, None)

        if not api_key:
            errors.append(
                f"LLM API key missing: {env_var} is required for {provider} "
                f"(used by {client_type} client). Set it in .env file."
            )

    if errors:
        error_msg = "API Key Validation Failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise RuntimeError(error_msg)

    log.info(
        "api_keys_validated",
        extraction=extraction_provider,
        scoring=scoring_provider,
        generation=generation_provider,
    )

    return []  # No errors


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

    # Validate API keys before initializing database
    # Fail fast if LLM providers are misconfigured
    validate_api_keys()

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

# Correlation ID middleware (added after CORS, before exception handlers)
app.add_middleware(CorrelationIDMiddleware)

# Setup exception handlers
setup_exception_handlers(app)

# Include routers
app.include_router(health.router, tags=["system"])
app.include_router(sessions.router)
app.include_router(synthetic.router)

# Register concepts router
app.include_router(concepts_router)

# Register simulation router
app.include_router(simulation_router)


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
