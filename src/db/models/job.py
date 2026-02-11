"""Modelo de Job para la base de datos."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, Text, Enum, DateTime, JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

from src.db.base import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(20), default=JobStatus.PENDING.value, index=True)
    progress = Column(Integer, default=0)

    # Input
    audio_file_path = Column(String, nullable=False)
    audio_filename = Column(String)
    audio_duration = Column(Float)
    model_size = Column(String, default="tiny")
    confidence_threshold = Column(Float, default=0.5)

    # Output
    result_data = Column(JSON)
    midi_file_path = Column(String)
    json_file_path = Column(String)
    notes_detected = Column(Integer)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processing_time = Column(Float)

    # Error
    error_message = Column(Text)

    # Webhook
    webhook_url = Column(String)
    webhook_sent = Column(Integer, default=0)  # SQLite no tiene boolean

    def to_dict(self) -> dict:
        return {
            "job_id": self.id,
            "status": self.status,
            "progress": self.progress,
            "audio_filename": self.audio_filename,
            "audio_duration": self.audio_duration,
            "model_size": self.model_size,
            "notes_detected": self.notes_detected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time": self.processing_time,
            "error_message": self.error_message,
        }
