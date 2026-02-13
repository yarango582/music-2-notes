"""Preprocesamiento de audio antes de la detección de pitch."""

import numpy as np
import librosa


def preprocess_audio(
    audio: np.ndarray,
    sr: int,
    trim_silence: bool = True,
    normalize: bool = True,
    top_db: int = 30,
) -> tuple[np.ndarray, float]:
    """
    Preprocesa audio para mejorar la detección de pitch.

    Args:
        audio: Array numpy con muestras de audio (mono)
        sr: Sample rate
        trim_silence: Recortar silencio al inicio y final
        normalize: Normalizar amplitud
        top_db: Umbral en dB para trim de silencio

    Returns:
        Tupla (audio_preprocesado, offset_seconds).
        offset_seconds indica cuántos segundos de silencio se recortaron
        del inicio, para sumar ese offset a los timestamps de las notas
        y mantener la sincronización con el audio original.
    """
    offset_seconds = 0.0

    if len(audio) == 0:
        return audio, offset_seconds

    # 1. Normalizar amplitud (pico a 1.0)
    if normalize:
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak

    # 2. Recortar silencio al inicio y final
    if trim_silence:
        audio_trimmed, trim_indices = librosa.effects.trim(audio, top_db=top_db)
        # trim_indices = [start_sample, end_sample] de la region no silenciosa
        offset_seconds = trim_indices[0] / sr
        audio = audio_trimmed

    return audio, offset_seconds


def compute_frame_energy(audio: np.ndarray, sr: int, hop_ms: float = 10.0) -> np.ndarray:
    """
    Calcula la energía RMS por frame del audio.

    Args:
        audio: Array numpy de audio
        sr: Sample rate
        hop_ms: Tamaño del hop en milisegundos

    Returns:
        Array con energía RMS por frame
    """
    hop_samples = int(sr * hop_ms / 1000.0)
    n_frames = len(audio) // hop_samples + 1

    energy = np.zeros(n_frames)
    for i in range(n_frames):
        start = i * hop_samples
        end = min(start + hop_samples, len(audio))
        if end > start:
            energy[i] = np.sqrt(np.mean(audio[start:end] ** 2))

    return energy


def compute_energy_threshold(energy: np.ndarray, percentile: float = 15.0) -> float:
    """
    Calcula un umbral adaptivo de energía para separar voz de silencio.

    El umbral se basa en un percentil bajo de la energia (los frames mas
    silenciosos), con un minimo y maximo para evitar filtrar demasiado.

    Args:
        energy: Array de energía por frame
        percentile: Percentil para el umbral (default: 15)

    Returns:
        Umbral de energía
    """
    threshold = np.percentile(energy, percentile)
    # Minimo: no filtrar nada si todo es silencio
    # Maximo: nunca usar mas del 10% de la energia mediana como umbral
    median_energy = np.median(energy)
    cap = median_energy * 0.1
    return max(min(threshold, cap), 0.005)
