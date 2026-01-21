"""
Health check endpoints.

Provides system health information for monitoring.
"""

from fastapi import APIRouter
import structlog

from src.core.config import settings
from src.persistence.database import check_database_health

log = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        System health status including database connectivity.
    """
    db_health = await check_database_health()

    overall_status = "healthy" if db_health["status"] == "healthy" else "unhealthy"

    return {
        "status": overall_status,
        "version": "0.1.0",
        "debug": settings.debug,
        "components": {
            "database": db_health
        }
    }


@router.get("/health/live")
async def liveness():
    """
    Kubernetes-style liveness probe.

    Returns 200 if the application is running.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness():
    """
    Kubernetes-style readiness probe.

    Returns 200 if the application is ready to serve requests.
    """
    db_health = await check_database_health()

    if db_health["status"] != "healthy":
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database not ready")

    return {"status": "ready"}
