"""Endpoints de Jobs."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.base import get_session
from src.db.repositories.job_repo import create_job, get_job
from src.storage.local import storage
from src.workers.audio_worker import process_audio_job
from src.api.models.responses import JobCreatedResponse, JobStatusResponse, JobResultResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Set para rastrear tasks en background
_background_tasks: set[asyncio.Task] = set()


@router.post("", status_code=202, response_model=JobCreatedResponse)
async def create_audio_job(
    audio_file: UploadFile = File(..., description="Archivo de audio (WAV, MP3, FLAC)"),
    model_size: str = Form(default="tiny", description="Modelo: tiny o full"),
    confidence_threshold: float = Form(default=0.95, description="Umbral de confianza (0.95 recomendado)"),
    webhook_url: str | None = Form(default=None, description="URL de webhook"),
    session: AsyncSession = Depends(get_session),
):
    """
    Crea un nuevo job de análisis de audio.

    Sube un archivo de audio y recibe un job_id para consultar el resultado.
    Opcionalmente registra un webhook_url para notificación automática.
    """
    # Validar modelo
    if model_size not in ("tiny", "full"):
        raise HTTPException(400, f"Modelo no válido: {model_size}. Usa 'tiny' o 'full'")

    # Validar archivo
    if not audio_file.filename:
        raise HTTPException(400, "Se requiere un archivo de audio")

    ext = Path(audio_file.filename).suffix.lower()
    if ext not in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
        raise HTTPException(422, f"Formato no soportado: {ext}")

    # Leer contenido
    content = await audio_file.read()

    if len(content) > settings.MAX_AUDIO_FILE_SIZE:
        raise HTTPException(413, "Archivo demasiado grande (máx 100MB)")

    if len(content) == 0:
        raise HTTPException(400, "Archivo vacío")

    # Crear job en BD
    job = await create_job(
        session,
        audio_file_path="",  # Se actualiza después de guardar
        audio_filename=audio_file.filename,
        model_size=model_size,
        confidence_threshold=confidence_threshold,
        webhook_url=webhook_url,
    )

    # Guardar archivo en storage
    file_path = await storage.save_upload(content, job.id, audio_file.filename)
    job.audio_file_path = file_path
    await session.commit()

    # Lanzar procesamiento en background
    task = asyncio.create_task(process_audio_job(job.id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return JobCreatedResponse(
        job_id=job.id,
        status=job.status,
        created_at=job.created_at.isoformat(),
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Consulta el estado y progreso de un job."""
    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")

    return JobStatusResponse(**job.to_dict())


@router.get("/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(
    job_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Obtiene el resultado completo de un job completado."""
    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")

    if job.status != "completed":
        raise HTTPException(
            400,
            f"Job aún no completado. Estado: {job.status}, progreso: {job.progress}%",
        )

    return JobResultResponse(
        job_id=job.id,
        status=job.status,
        result=job.result_data,
    )


@router.get("/{job_id}/download/midi")
async def download_midi(
    job_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Descarga el archivo MIDI generado."""
    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")

    if job.status != "completed" or not job.midi_file_path:
        raise HTTPException(400, "MIDI no disponible aún")

    path = Path(job.midi_file_path)
    if not path.exists():
        raise HTTPException(404, "Archivo MIDI no encontrado en storage")

    return FileResponse(
        path=str(path),
        media_type="audio/midi",
        filename=path.name,
    )


@router.get("/{job_id}/download/json")
async def download_json(
    job_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Descarga el archivo JSON con las notas detectadas."""
    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")

    if job.status != "completed" or not job.json_file_path:
        raise HTTPException(400, "JSON no disponible aún")

    path = Path(job.json_file_path)
    if not path.exists():
        raise HTTPException(404, "Archivo JSON no encontrado en storage")

    return FileResponse(
        path=str(path),
        media_type="application/json",
        filename=path.name,
    )
