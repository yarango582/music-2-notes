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
from src.audio.pitch_post_processor import post_process_pitch
from src.audio.note_segmenter import (
    segment_notes, merge_same_pitch_notes, refine_onsets, filter_short_notes,
)
from src.audio.key_detector import filter_key_outliers, format_key_info
from src.audio.midi_generator import generate_midi
from src.audio.json_formatter import format_result, save_json
from src.core.config import settings
from src.core.security import generate_webhook_signature
from src.db.base import async_session
from src.db.models.job import JobStatus
from src.db.repositories.job_repo import (
    get_job, update_job_status, complete_job, fail_job,
)


def _stage_load(audio_file_path: str):
    """Stage 1: Load and preprocess audio."""
    info = get_audio_info(audio_file_path)
    audio, sr = load_audio(audio_file_path, target_sr=16000, mono=True)
    audio, trim_offset = preprocess_audio(audio, sr)
    return info, audio, sr, trim_offset


def _stage_detect(audio, sr, model_size: str):
    """Stage 2: Detect pitch (heaviest step — torch/CREPE)."""
    frames = detect_pitches(
        audio, sr, model_size=model_size,
        batch_size=settings.CREPE_BATCH_SIZE,
        fmin=settings.CREPE_FMIN,
        fmax=settings.CREPE_FMAX,
    )
    frames = post_process_pitch(
        frames,
        median_window=settings.PITCH_MEDIAN_WINDOW,
        vibrato_smooth_window=settings.VIBRATO_SMOOTH_WINDOW,
        vibrato_extent_cents=settings.VIBRATO_EXTENT_CENTS,
    )
    return frames


def _stage_segment(frames, audio, sr, trim_offset: float, confidence_threshold: float):
    """Stage 3: Segment, merge, filter notes + key detection."""
    energy = compute_frame_energy(audio, sr)
    threshold = compute_energy_threshold(energy)
    notes = segment_notes(
        frames, energy=energy, energy_threshold=threshold,
        confidence_threshold=confidence_threshold,
        time_offset=trim_offset,
    )
    notes = merge_same_pitch_notes(notes, max_gap=settings.NOTE_MERGE_MAX_GAP)
    notes = refine_onsets(
        notes, energy=energy, time_offset=trim_offset,
        lookback_frames=settings.ONSET_LOOKBACK_FRAMES,
    )
    notes = filter_short_notes(notes, min_duration=settings.POST_MERGE_MIN_DURATION)
    notes, section_keys = filter_key_outliers(notes)
    key_info = format_key_info(section_keys) if section_keys else None
    return notes, key_info


def _stage_output(notes, key_info, info: dict, audio_filename: str, model_size: str,
                  confidence_threshold: float, job_id: str):
    """Stage 4: Generate MIDI, JSON outputs."""
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
        key_info=key_info,
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
    Procesa un job de audio en etapas con progreso real.

    Cada etapa pesada se ejecuta en un thread separado
    para no bloquear el event loop de FastAPI.
    """
    async with async_session() as session:
        try:
            job = await get_job(session, job_id)
            if not job:
                return

            # 10% — Loading audio
            await update_job_status(session, job_id, JobStatus.PROCESSING, progress=10)
            info, audio, sr, trim_offset = await asyncio.to_thread(
                _stage_load, job.audio_file_path,
            )

            # 30% — Detecting pitch (heaviest step)
            await update_job_status(session, job_id, JobStatus.PROCESSING, progress=30)
            frames = await asyncio.to_thread(
                _stage_detect, audio, sr, job.model_size,
            )

            # 60% — Segmenting notes
            await update_job_status(session, job_id, JobStatus.PROCESSING, progress=60)
            notes, key_info = await asyncio.to_thread(
                _stage_segment, frames, audio, sr, trim_offset, job.confidence_threshold,
            )

            # 90% — Generating outputs
            await update_job_status(session, job_id, JobStatus.PROCESSING, progress=90)
            result = await asyncio.to_thread(
                _stage_output, notes, key_info, info, job.audio_filename,
                job.model_size, job.confidence_threshold, job_id,
            )

            # 100% — Complete
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
