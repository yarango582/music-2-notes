"""Router principal de la API v1."""

from fastapi import APIRouter

from src.api.v1.jobs import router as jobs_router
from src.api.v1.health import router as health_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(jobs_router)
v1_router.include_router(health_router)
