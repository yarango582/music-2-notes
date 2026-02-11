"""Modelos Pydantic para responses de la API."""

from pydantic import BaseModel
from typing import Any


class JobCreatedResponse(BaseModel):
    job_id: str
    status: str = "pending"
    created_at: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    audio_filename: str | None = None
    audio_duration: float | None = None
    model_size: str | None = None
    notes_detected: int | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    processing_time: float | None = None
    error_message: str | None = None


class NoteResponse(BaseModel):
    midi_number: int
    note_name: str
    start_time: float
    duration: float
    end_time: float
    frequency: float
    confidence: float
    velocity: int


class JobResultResponse(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str
    database: str
    storage: str
