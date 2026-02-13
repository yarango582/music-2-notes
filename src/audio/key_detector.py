"""Detección de tonalidad por secciones y filtrado tonal de outliers."""

from dataclasses import dataclass

import numpy as np

from src.audio.models import Note
from src.core.config import settings


# Krumhansl-Kessler key profiles.
# Índice 0 = tónica. Fuente: Krumhansl, "Cognitive Foundations of Musical Pitch" (1990).
MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Grados diatónicos (offsets en semitonos desde la tónica)
_MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11}
_MINOR_SCALE = {0, 2, 3, 5, 7, 8, 10}  # menor natural


@dataclass
class SectionKey:
    """Tonalidad detectada para una sección temporal."""
    start_time: float
    end_time: float
    key_name: str       # ej: "C major", "A minor"
    tonic: int          # pitch class 0-11 (0=C)
    mode: str           # "major" o "minor"
    correlation: float  # confianza de la detección (0-1)


def detect_section_keys(
    notes: list[Note],
    window_seconds: float = settings.KEY_WINDOW_SECONDS,
    overlap_seconds: float = settings.KEY_OVERLAP_SECONDS,
) -> list[SectionKey]:
    """
    Detecta la tonalidad en ventanas superpuestas a lo largo de la canción.

    Usa el algoritmo Krumhansl-Schmuckler: construye un histograma de pitch classes
    ponderado por duración y lo correlaciona con los 24 perfiles de key.

    Args:
        notes: Lista de notas ordenadas por tiempo
        window_seconds: Tamaño de la ventana en segundos
        overlap_seconds: Solapamiento entre ventanas

    Returns:
        Lista de SectionKey, una por ventana temporal
    """
    if not notes:
        return []

    song_start = notes[0].start_time
    song_end = notes[-1].end_time
    total_duration = song_end - song_start

    if total_duration <= 0:
        return []

    step = window_seconds - overlap_seconds
    if step <= 0:
        step = window_seconds

    sections: list[SectionKey] = []
    w_start = song_start

    while w_start < song_end:
        w_end = w_start + window_seconds

        # Construir histograma ponderado por duración dentro de la ventana
        histogram = np.zeros(12, dtype=np.float64)

        for note in notes:
            if note.start_time >= w_end or note.end_time <= w_start:
                continue
            # Duración de la nota dentro de la ventana
            overlap_start = max(note.start_time, w_start)
            overlap_end = min(note.end_time, w_end)
            weight = overlap_end - overlap_start
            if weight > 0:
                pc = note.midi_number % 12
                histogram[pc] += weight

        # Solo analizar si hay suficiente material
        if histogram.sum() > 0.1:
            tonic, mode, corr = _find_best_key(histogram)
            key_name = f"{_NOTE_NAMES[tonic]} {mode}"
            sections.append(SectionKey(
                start_time=w_start,
                end_time=min(w_end, song_end),
                key_name=key_name,
                tonic=tonic,
                mode=mode,
                correlation=corr,
            ))

        w_start += step

    return sections


def _find_best_key(histogram: np.ndarray) -> tuple[int, str, float]:
    """
    Encuentra la mejor tonalidad para un histograma de pitch classes.

    Prueba los 24 keys posibles (12 tónicas × 2 modos), calcula la correlación
    de Pearson con cada perfil rotado, y retorna el mejor.

    Returns:
        (tonic, mode, correlation) donde correlation está normalizado a 0-1
    """
    best_tonic = 0
    best_mode = "major"
    best_corr = -2.0

    for tonic in range(12):
        for mode, profile in [("major", MAJOR_PROFILE), ("minor", MINOR_PROFILE)]:
            # Rotar el perfil para que índice 0 alinee con la tónica candidata
            rotated = np.array([profile[(i - tonic) % 12] for i in range(12)])
            # Correlación de Pearson
            corr = np.corrcoef(histogram, rotated)[0, 1]
            if np.isnan(corr):
                continue
            if corr > best_corr:
                best_corr = corr
                best_tonic = tonic
                best_mode = mode

    # Normalizar correlación de [-1, 1] a [0, 1]
    normalized = (best_corr + 1.0) / 2.0
    return best_tonic, best_mode, round(normalized, 4)


def _build_extended_scale(tonic: int, mode: str) -> set[int]:
    """
    Construye el set de pitch classes 'permitidos': diatónicos + vecinos cromáticos.

    Para una escala de 7 notas, agregar vecinos ±1 semitono típicamente produce
    10-11 de los 12 pitch classes posibles, haciendo el filtrado muy conservador.
    """
    base = _MAJOR_SCALE if mode == "major" else _MINOR_SCALE
    diatonic = {(tonic + interval) % 12 for interval in base}
    extended = set(diatonic)
    for pc in diatonic:
        extended.add((pc - 1) % 12)
        extended.add((pc + 1) % 12)
    return extended


def filter_key_outliers(
    notes: list[Note],
    window_seconds: float = settings.KEY_WINDOW_SECONDS,
    overlap_seconds: float = settings.KEY_OVERLAP_SECONDS,
    max_duration: float = settings.KEY_OUTLIER_MAX_DURATION,
    max_confidence: float = settings.KEY_OUTLIER_MAX_CONFIDENCE,
) -> tuple[list[Note], list[SectionKey]]:
    """
    Filtra notas que son outliers tonales con criterio triple conservador.

    Una nota solo se elimina si cumple LAS TRES condiciones:
    1. Su pitch class NO está en la escala extendida de la sección
    2. Su duración es menor a max_duration (150ms por defecto)
    3. Su confianza es menor a max_confidence (0.65 por defecto)

    Esto asegura que notas largas, notas con alta confianza, o notas cromáticas
    intencionales se preserven.

    Args:
        notes: Lista de notas
        window_seconds: Tamaño de ventana para detección de key
        overlap_seconds: Solapamiento entre ventanas
        max_duration: Solo filtrar notas más cortas que esto
        max_confidence: Solo filtrar notas con confianza menor a esto

    Returns:
        Tupla (notas_filtradas, secciones_detectadas)
    """
    if not notes:
        return notes, []

    section_keys = detect_section_keys(notes, window_seconds, overlap_seconds)

    if not section_keys:
        return notes, []

    filtered: list[Note] = []

    for note in notes:
        # Encontrar la sección con mayor correlación que cubre esta nota
        best_section: SectionKey | None = None
        best_corr = -1.0

        for sk in section_keys:
            if note.start_time < sk.end_time and note.end_time > sk.start_time:
                if sk.correlation > best_corr:
                    best_corr = sk.correlation
                    best_section = sk

        if best_section is None:
            # Nota fuera de todas las secciones — mantener
            filtered.append(note)
            continue

        allowed = _build_extended_scale(best_section.tonic, best_section.mode)
        pc = note.midi_number % 12

        # Triple condición: solo eliminar si TODAS se cumplen
        is_tonal_outlier = pc not in allowed
        is_short = note.duration < max_duration
        is_low_confidence = note.confidence < max_confidence

        if is_tonal_outlier and is_short and is_low_confidence:
            continue  # Eliminar
        else:
            filtered.append(note)

    return filtered, section_keys


def format_key_info(section_keys: list[SectionKey]) -> list[dict]:
    """Convierte secciones de key a dicts serializables para JSON."""
    return [
        {
            "start_time": round(sk.start_time, 2),
            "end_time": round(sk.end_time, 2),
            "key": sk.key_name,
            "tonic": sk.tonic,
            "mode": sk.mode,
            "correlation": round(sk.correlation, 3),
        }
        for sk in section_keys
    ]
