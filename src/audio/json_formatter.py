"""Formateo de resultados en JSON."""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.audio.models import Note


def format_result(
    notes: list[Note],
    audio_duration: float,
    model_size: str,
    confidence_threshold: float,
    input_file: str | None = None,
) -> dict:
    """
    Formatea los resultados del análisis como diccionario.

    Args:
        notes: Lista de notas detectadas
        audio_duration: Duración del audio en segundos
        model_size: Modelo CREPE usado
        confidence_threshold: Umbral de confianza usado
        input_file: Nombre del archivo de entrada (opcional)

    Returns:
        Diccionario con metadata y notas
    """
    return {
        "metadata": {
            "input_file": input_file,
            "audio_duration": round(audio_duration, 2),
            "model_size": model_size,
            "confidence_threshold": confidence_threshold,
            "notes_detected": len(notes),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
        "notes": [note.to_dict() for note in notes],
    }


def save_json(data: dict, output_path: str | Path) -> Path:
    """
    Guarda resultados como archivo JSON.

    Args:
        data: Diccionario con los resultados
        output_path: Ruta de salida

    Returns:
        Path del archivo generado
    """
    output_path = Path(output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_path
