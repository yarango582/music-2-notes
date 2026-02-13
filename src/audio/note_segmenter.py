"""Segmentación de pitch frames en notas musicales discretas."""

import numpy as np

from src.audio.models import Note, PitchFrame
from src.utils.converters import hz_to_midi, midi_to_note_name


def segment_notes(
    frames: list[PitchFrame],
    energy: np.ndarray | None = None,
    energy_threshold: float = 0.01,
    confidence_threshold: float = 0.95,
    min_freq: float = 80.0,
    min_note_duration: float = 0.05,
    time_offset: float = 0.0,
) -> list[Note]:
    """
    Convierte una secuencia de PitchFrames en notas musicales discretas.

    Agrupa frames consecutivos con el mismo número MIDI en una sola nota.
    Filtra por energía (si se provee), confianza del modelo y frecuencia mínima.

    Args:
        frames: Lista de PitchFrame del pitch detector
        energy: Array de energía RMS por frame (opcional)
        energy_threshold: Umbral mínimo de energía
        confidence_threshold: Umbral mínimo de confianza del modelo (0-1)
        min_freq: Frecuencia mínima en Hz (por debajo se considera ruido)
        min_note_duration: Duración mínima de una nota en segundos
        time_offset: Offset en segundos para sumar a los timestamps (ej: silencio
            recortado del inicio del audio original)

    Returns:
        Lista de notas musicales detectadas, ordenadas por tiempo
    """
    if not frames:
        return []

    notes: list[Note] = []
    current_midi: int | None = None
    note_start: float = 0.0
    note_freqs: list[float] = []
    note_confs: list[float] = []

    for i, frame in enumerate(frames):
        # Determinar si el frame es válido
        has_energy = True
        if energy is not None and i < len(energy):
            has_energy = energy[i] > energy_threshold

        is_valid = frame.frequency > min_freq and frame.confidence >= confidence_threshold and has_energy

        if is_valid:
            midi_num = hz_to_midi(frame.frequency)

            if current_midi is None:
                # Iniciar nueva nota
                current_midi = midi_num
                note_start = frame.time
                note_freqs = [frame.frequency]
                note_confs = [frame.confidence]

            elif midi_num == current_midi:
                # Continuar nota actual
                note_freqs.append(frame.frequency)
                note_confs.append(frame.confidence)

            else:
                # Cambio de nota: guardar anterior
                _maybe_add_note(
                    notes, current_midi, note_start, frame.time,
                    note_freqs, note_confs, min_note_duration, time_offset,
                )
                # Iniciar nueva
                current_midi = midi_num
                note_start = frame.time
                note_freqs = [frame.frequency]
                note_confs = [frame.confidence]
        else:
            # Silencio o ruido: cerrar nota actual
            if current_midi is not None:
                _maybe_add_note(
                    notes, current_midi, note_start, frame.time,
                    note_freqs, note_confs, min_note_duration, time_offset,
                )
                current_midi = None
                note_freqs = []
                note_confs = []

    # Cerrar última nota si existe
    if current_midi is not None and note_freqs:
        end_time = frames[-1].time + 0.01  # Agregar un frame más
        _maybe_add_note(
            notes, current_midi, note_start, end_time,
            note_freqs, note_confs, min_note_duration, time_offset,
        )

    return notes


def _maybe_add_note(
    notes: list[Note],
    midi_number: int,
    start_time: float,
    end_time: float,
    frequencies: list[float],
    confidences: list[float],
    min_duration: float,
    time_offset: float = 0.0,
) -> None:
    """Agrega una nota a la lista si cumple con la duración mínima."""
    duration = end_time - start_time
    if duration < min_duration or not frequencies:
        return

    avg_freq = sum(frequencies) / len(frequencies)
    avg_conf = sum(confidences) / len(confidences)

    notes.append(
        Note(
            midi_number=midi_number,
            note_name=midi_to_note_name(midi_number),
            start_time=round(start_time + time_offset, 4),
            duration=round(duration, 4),
            frequency=round(avg_freq, 2),
            confidence=round(avg_conf, 3),
        )
    )
