"""Repositorio de operaciones CRUD para Jobs."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.job import Job, JobStatus


async def create_job(
    session: AsyncSession,
    audio_file_path: str,
    audio_filename: str,
    model_size: str = "tiny",
    confidence_threshold: float = 0.5,
    webhook_url: str | None = None,
) -> Job:
    """Crea un nuevo job en la base de datos."""
    job = Job(
        audio_file_path=audio_file_path,
        audio_filename=audio_filename,
        model_size=model_size,
        confidence_threshold=confidence_threshold,
        webhook_url=webhook_url,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_job(session: AsyncSession, job_id: str) -> Job | None:
    """Obtiene un job por su ID."""
    result = await session.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def update_job_status(
    session: AsyncSession,
    job_id: str,
    status: JobStatus,
    progress: int | None = None,
    **kwargs,
) -> Job | None:
    """Actualiza el estado de un job."""
    job = await get_job(session, job_id)
    if not job:
        return None

    job.status = status.value

    if progress is not None:
        job.progress = progress

    if status == JobStatus.PROCESSING and job.started_at is None:
        job.started_at = datetime.utcnow()

    if status in (JobStatus.COMPLETED, JobStatus.FAILED):
        completed = datetime.utcnow()
        job.completed_at = completed
        if job.started_at:
            # Strip tzinfo to avoid naive vs aware mismatch from SQLite
            started = job.started_at.replace(tzinfo=None)
            delta = completed - started
            job.processing_time = delta.total_seconds()

    for key, value in kwargs.items():
        if hasattr(job, key):
            setattr(job, key, value)

    await session.commit()
    await session.refresh(job)
    return job


async def complete_job(
    session: AsyncSession,
    job_id: str,
    result_data: dict,
    midi_file_path: str,
    json_file_path: str,
    notes_detected: int,
    audio_duration: float,
) -> Job | None:
    """Marca un job como completado con sus resultados."""
    return await update_job_status(
        session,
        job_id,
        JobStatus.COMPLETED,
        progress=100,
        result_data=result_data,
        midi_file_path=midi_file_path,
        json_file_path=json_file_path,
        notes_detected=notes_detected,
        audio_duration=audio_duration,
    )


async def fail_job(
    session: AsyncSession,
    job_id: str,
    error_message: str,
) -> Job | None:
    """Marca un job como fallido."""
    return await update_job_status(
        session,
        job_id,
        JobStatus.FAILED,
        error_message=error_message,
    )
