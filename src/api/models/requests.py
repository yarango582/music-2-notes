"""Modelos Pydantic para requests de la API."""

from pydantic import BaseModel, Field
from typing import Literal


class JobOptions(BaseModel):
    model_size: Literal["tiny", "full"] = Field(
        default="tiny",
        description="Modelo CREPE: tiny (rápido) o full (preciso)",
    )
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Umbral de confianza del modelo CREPE (0.5 recomendado con post-procesamiento)",
    )
    webhook_url: str | None = Field(
        default=None,
        description="URL para recibir notificación cuando el job complete",
    )
