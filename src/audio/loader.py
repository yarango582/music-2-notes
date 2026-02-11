"""
Módulo para cargar y validar archivos de audio.
"""

from pathlib import Path
from typing import Tuple

import librosa
import numpy as np
import soundfile as sf


class AudioLoadError(Exception):
    """Error al cargar archivo de audio."""

    pass


def load_audio(
    file_path: str | Path,
    target_sr: int = 16000,
    mono: bool = True,
    duration: float | None = None,
    offset: float = 0.0,
) -> Tuple[np.ndarray, int]:
    """
    Carga un archivo de audio y lo convierte al formato requerido.

    Args:
        file_path: Ruta al archivo de audio (WAV, MP3, FLAC, etc.)
        target_sr: Sample rate objetivo en Hz (default: 16000 para CREPE)
        mono: Si True, convierte a mono (default: True)
        duration: Duración máxima a cargar en segundos (None = todo el archivo)
        offset: Tiempo de inicio en segundos (default: 0.0)

    Returns:
        Tuple de (audio, sample_rate)
        - audio: numpy array con las muestras de audio
        - sample_rate: sample rate del audio

    Raises:
        AudioLoadError: Si el archivo no existe, está corrupto o no es soportado

    Example:
        >>> audio, sr = load_audio("song.wav")
        >>> audio, sr = load_audio("song.mp3", target_sr=22050)
    """
    file_path = Path(file_path)

    # Validar que el archivo existe
    if not file_path.exists():
        raise AudioLoadError(f"Archivo no encontrado: {file_path}")

    # Validar extensión
    supported_formats = [".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"]
    if file_path.suffix.lower() not in supported_formats:
        raise AudioLoadError(
            f"Formato no soportado: {file_path.suffix}. "
            f"Formatos soportados: {', '.join(supported_formats)}"
        )

    try:
        # Cargar audio con librosa (maneja múltiples formatos)
        audio, sr = librosa.load(
            str(file_path),
            sr=target_sr,
            mono=mono,
            duration=duration,
            offset=offset,
        )

        # Validar que se cargó algo
        if len(audio) == 0:
            raise AudioLoadError(f"Archivo de audio vacío: {file_path}")

        # Validar duración mínima (100ms)
        min_duration = 0.1  # segundos
        actual_duration = len(audio) / sr
        if actual_duration < min_duration:
            raise AudioLoadError(
                f"Audio demasiado corto: {actual_duration:.2f}s "
                f"(mínimo: {min_duration}s)"
            )

        return audio, sr

    except librosa.LibrosaError as e:
        raise AudioLoadError(f"Error al cargar audio con librosa: {e}")
    except Exception as e:
        raise AudioLoadError(f"Error inesperado al cargar audio: {e}")


def get_audio_info(file_path: str | Path) -> dict:
    """
    Obtiene información del archivo de audio sin cargarlo completamente.

    Args:
        file_path: Ruta al archivo de audio

    Returns:
        Diccionario con información del audio:
        - duration: duración en segundos
        - sample_rate: sample rate original
        - channels: número de canales
        - format: formato del archivo

    Raises:
        AudioLoadError: Si no se puede leer el archivo

    Example:
        >>> info = get_audio_info("song.wav")
        >>> print(f"Duración: {info['duration']:.2f}s")
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise AudioLoadError(f"Archivo no encontrado: {file_path}")

    try:
        # Usar soundfile para obtener info rápidamente
        info = sf.info(str(file_path))

        return {
            "duration": info.duration,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "format": info.format,
            "subtype": info.subtype,
        }

    except Exception as e:
        # Fallback a librosa si soundfile falla
        try:
            duration = librosa.get_duration(path=str(file_path))
            return {
                "duration": duration,
                "sample_rate": None,  # No disponible sin cargar
                "channels": None,
                "format": file_path.suffix,
                "subtype": None,
            }
        except Exception as e2:
            raise AudioLoadError(f"Error obteniendo info del audio: {e2}")


def validate_audio_file(file_path: str | Path, max_duration: float = 600) -> None:
    """
    Valida que un archivo de audio es procesable.

    Args:
        file_path: Ruta al archivo de audio
        max_duration: Duración máxima permitida en segundos (default: 10 min)

    Raises:
        AudioLoadError: Si el archivo no es válido

    Example:
        >>> validate_audio_file("song.wav")  # OK si es válido
        >>> validate_audio_file("too_long.wav", max_duration=60)  # Error si > 60s
    """
    file_path = Path(file_path)

    # Verificar existencia
    if not file_path.exists():
        raise AudioLoadError(f"Archivo no encontrado: {file_path}")

    # Verificar tamaño
    max_size_mb = 100
    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise AudioLoadError(
            f"Archivo demasiado grande: {size_mb:.2f}MB (máximo: {max_size_mb}MB)"
        )

    # Obtener info y validar duración
    info = get_audio_info(file_path)
    if info["duration"] > max_duration:
        raise AudioLoadError(
            f"Audio demasiado largo: {info['duration']:.2f}s "
            f"(máximo: {max_duration}s)"
        )

    if info["duration"] < 0.1:
        raise AudioLoadError(
            f"Audio demasiado corto: {info['duration']:.2f}s (mínimo: 0.1s)"
        )
