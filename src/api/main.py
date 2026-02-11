"""FastAPI application principal."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.db.base import init_db
from src.api.v1.router import v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y cleanup de la aplicación."""
    # Startup: crear tablas y carpetas
    Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    Path(settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")).parent.mkdir(
        parents=True, exist_ok=True
    )
    await init_db()
    yield
    # Shutdown: nada por ahora


app = FastAPI(
    title="Music-2-Notes API",
    description=(
        "API para análisis de audio vocal. "
        "Detecta notas musicales y genera archivos MIDI."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas
app.include_router(v1_router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "Music-2-Notes API",
        "version": "0.1.0",
        "docs": "/docs",
    }
