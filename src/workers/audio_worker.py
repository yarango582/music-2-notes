"""
Worker de procesamiento de audio.

Ejecuta el procesamiento pesado (torch/CREPE) en un thread separado
para no bloquear el event loop de FastAPI.
"""

import asyncio
import traceback
from pathlib import Path

import httpx

from src.audio.loader import load_audio, get_audio_info
from src.audio.preprocessor import preprocess_audio, compute_frame_energy, compute_energy_threshold
from src.audio.pitch_detector import detect_pitches
from src.audio.note_segmenter import segment_notes
from src.audio.midi_generator import generate_midi
from src.audio.json_formatter import format_result, save_json
from src.core.config import settings
from src.core.security import generate_webhook_signature
from src.db.base import async_session
from src.db.models.job import JobStatus
from src.db.repositories.job_repo import (
    get_job, update_job_status, complete_job, fail_job,
)


def _run_audio_pipeline(
    audio_file_path: str,
    model_size: str,
    confidence_threshold: float,
    audio_filename: str,
    job_id: str,
) -> dict:
    """
    Ejecuta el pipeline de audio SINCRONAMENTE (CPU-bound).
    Se llama desde un thread para no bloquear asyncio.
    """
    # 1. Info del audio
    info = get_audio_info(audio_file_path)

    # 2. Cargar audio
    audio, sr = load_audio(audio_file_path, target_sr=16000, mono=True)

    # 3. Preprocesar (retorna offset del silencio recortado al inicio)
    audio, trim_offset = preprocess_audio(audio, sr)

    # 4. Detectar pitch
    frames = detect_pitches(audio, sr, model_size=model_size)

    # 5. Calcular energía y segmentar notas
    #    El trim_offset se suma a los timestamps para mantener sincronización
    #    con el audio original (ej: si la canción tiene 23s de intro instrumental)
    energy = compute_frame_energy(audio, sr)
    threshold = compute_energy_threshold(energy)
    notes = segment_notes(
        frames, energy=energy, energy_threshold=threshold,
        confidence_threshold=confidence_threshold,
        time_offset=trim_offset,
    )

    # 6. Generar outputs
    results_dir = Path(settings.STORAGE_PATH) / "results" / job_id
    results_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(audio_filename or "output").stem

    midi_path = generate_midi(notes, results_dir / f"{stem}.mid")

    result_data = format_result(
        notes=notes,
        audio_duration=info["duration"],
        model_size=model_size,
        confidence_threshold=confidence_threshold,
        input_file=audio_filename,
    )
    json_path = save_json(result_data, results_dir / f"{stem}.json")

    return {
        "result_data": result_data,
        "midi_file_path": str(midi_path),
        "json_file_path": str(json_path),
        "notes_detected": len(notes),
        "audio_duration": info["duration"],
    }


async def process_audio_job(job_id: str) -> None:
    """
    Procesa un job de audio completo.

    El trabajo pesado (torch) se ejecuta en un thread separado
    para no bloquear la API.
    """
    async with async_session() as session:
        try:
            job = await get_job(session, job_id)
            if not job:
                return

            # Marcar como procesando
            await update_job_status(session, job_id, JobStatus.PROCESSING, progress=5)

            # Ejecutar pipeline en thread separado (no bloquea la API)
            result = await asyncio.to_thread(
                _run_audio_pipeline,
                audio_file_path=job.audio_file_path,
                model_size=job.model_size,
                confidence_threshold=job.confidence_threshold,
                audio_filename=job.audio_filename,
                job_id=job_id,
            )

            # Completar job
            await complete_job(
                session,
                job_id,
                result_data=result["result_data"],
                midi_file_path=result["midi_file_path"],
                json_file_path=result["json_file_path"],
                notes_detected=result["notes_detected"],
                audio_duration=result["audio_duration"],
            )

            # Enviar webhook si configurado
            if job.webhook_url:
                await _send_webhook(job_id, job.webhook_url, result["result_data"])

        except Exception as e:
            async with async_session() as err_session:
                await fail_job(err_session, job_id, str(e))
            traceback.print_exc()


async def _send_webhook(job_id: str, webhook_url: str, result_data: dict) -> None:
    """Envía notificación webhook con retry y backoff exponencial."""
    payload = {
        "event": "job.completed",
        "job_id": job_id,
        "data": {
            "notes_detected": result_data["metadata"]["notes_detected"],
            "audio_duration": result_data["metadata"]["audio_duration"],
        },
    }

    signature = generate_webhook_signature(payload, settings.WEBHOOK_SECRET_KEY)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": "job.completed",
        "User-Agent": "Music2Notes/1.0",
    }

    for attempt in range(settings.WEBHOOK_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT) as client:
                response = await client.post(webhook_url, json=payload, headers=headers)
                if response.status_code < 300:
                    async with async_session() as session:
                        job = await get_job(session, job_id)
                        if job:
                            job.webhook_sent = 1
                            await session.commit()
                    return
        except Exception:
            pass

        await asyncio.sleep(2 ** attempt)
