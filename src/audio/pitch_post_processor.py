"""Post-procesamiento de pitch: filtrado mediano y suavizado de vibrato."""

import numpy as np
from scipy.ndimage import median_filter, uniform_filter1d

from src.audio.models import PitchFrame


def post_process_pitch(
    frames: list[PitchFrame],
    median_window: int = 5,
    vibrato_smooth_window: int = 13,
    vibrato_extent_cents: float = 120.0,
    min_voiced_confidence: float = 0.1,
) -> list[PitchFrame]:
    """
    Aplica filtrado mediano y suavizado de vibrato a pitch frames.

    1. Filtro mediano elimina jitter frame-a-frame (outliers de 1-2 frames).
    2. Suavizado de vibrato detecta oscilaciones periódicas y las reemplaza
       con la frecuencia central.

    Args:
        frames: Lista de PitchFrame del detector
        median_window: Ventana del filtro mediano en frames (5 = 50ms)
        vibrato_smooth_window: Ventana del moving average para vibrato (13 = 130ms)
        vibrato_extent_cents: Threshold de spread peak-to-peak en cents
        min_voiced_confidence: Confianza mínima para considerar un frame como voiced

    Returns:
        Lista de PitchFrame con frecuencias limpiadas
    """
    if len(frames) < median_window:
        return frames

    freqs = np.array([f.frequency for f in frames], dtype=np.float64)
    confs = np.array([f.confidence for f in frames], dtype=np.float64)

    # Paso 1: Filtro mediano (solo dentro de segmentos voiced)
    freqs = _segmented_median_filter(freqs, confs, median_window, min_voiced_confidence)

    # Paso 2: Suavizado de vibrato
    freqs = _smooth_vibrato(
        freqs, confs, vibrato_smooth_window, vibrato_extent_cents, min_voiced_confidence,
    )

    # Reconstruir PitchFrames con frecuencias limpiadas
    return [
        PitchFrame(
            time=frames[i].time,
            frequency=max(float(freqs[i]), 0.0),
            confidence=frames[i].confidence,
        )
        for i in range(len(frames))
    ]


def _segmented_median_filter(
    freqs: np.ndarray,
    confs: np.ndarray,
    window: int,
    min_confidence: float,
) -> np.ndarray:
    """Aplica filtro mediano solo dentro de segmentos voiced contiguos."""
    result = freqs.copy()
    voiced = (freqs > 0) & (confs > min_confidence)
    segments = _find_segments(voiced)

    for start, end in segments:
        if end - start >= window:
            result[start:end] = median_filter(
                freqs[start:end], size=window, mode="reflect",
            )

    return result


def _smooth_vibrato(
    freqs: np.ndarray,
    confs: np.ndarray,
    smooth_window: int,
    extent_threshold_cents: float,
    min_confidence: float,
) -> np.ndarray:
    """Detecta y suaviza regiones de vibrato."""
    result = freqs.copy()
    voiced = (freqs > 0) & (confs > min_confidence)
    segments = _find_segments(voiced)

    for start, end in segments:
        if end - start < smooth_window:
            continue

        segment = freqs[start:end]

        # Moving average como estimador de frecuencia central
        smoothed = uniform_filter1d(segment, size=smooth_window, mode="reflect")

        # Diferencia en cents entre raw y smoothed
        with np.errstate(divide="ignore", invalid="ignore"):
            cents_diff = 1200.0 * np.log2(segment / smoothed)
            cents_diff = np.nan_to_num(cents_diff, nan=0.0, posinf=0.0, neginf=0.0)

        # Detectar vibrato: std local de cents_diff en ventana ~260ms
        analysis_window = smooth_window * 2
        if len(cents_diff) >= analysis_window:
            local_std = _rolling_std(cents_diff, analysis_window)
            # std de una sinusoide ≈ amplitud / sqrt(2)
            # extent es peak-to-peak (2*amplitud), así que std ≈ extent / (2*sqrt(2))
            # Usamos extent/4 como threshold conservador
            vibrato_mask = local_std > (extent_threshold_cents / 4.0)
            result[start:end] = np.where(vibrato_mask, smoothed, segment)

    return result


def _find_segments(mask: np.ndarray) -> list[tuple[int, int]]:
    """Encuentra regiones contiguas True en un array booleano."""
    segments = []
    in_segment = False
    start = 0

    for i in range(len(mask)):
        if mask[i] and not in_segment:
            start = i
            in_segment = True
        elif not mask[i] and in_segment:
            segments.append((start, i))
            in_segment = False

    if in_segment:
        segments.append((start, len(mask)))

    return segments


def _rolling_std(arr: np.ndarray, window: int) -> np.ndarray:
    """Calcula std rolling usando sumas acumulativas (O(n))."""
    n = len(arr)
    result = np.zeros(n)
    if n < window:
        return result

    cumsum = np.cumsum(arr)
    cumsum2 = np.cumsum(arr ** 2)
    half = window // 2

    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        count = hi - lo
        s = cumsum[hi - 1] - (cumsum[lo - 1] if lo > 0 else 0)
        s2 = cumsum2[hi - 1] - (cumsum2[lo - 1] if lo > 0 else 0)
        variance = s2 / count - (s / count) ** 2
        result[i] = np.sqrt(max(0.0, variance))

    return result
