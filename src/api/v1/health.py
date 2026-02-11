"""Endpoint de health check."""

from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from src.core.config import settings
from src.db.base import async_session
from src.api.models.responses import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica que todos los servicios estén funcionando."""
    db_status = "up"
    storage_status = "up"

    # Check database
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"

    # Check storage
    storage_path = Path(settings.STORAGE_PATH)
    if not storage_path.exists():
        storage_status = "down"

    status = "healthy" if db_status == "up" and storage_status == "up" else "unhealthy"

    return HealthResponse(
        status=status,
        database=db_status,
        storage=storage_status,
    )
