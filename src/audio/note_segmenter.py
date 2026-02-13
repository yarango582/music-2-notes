"""Segmentación de pitch frames en notas musicales discretas."""

import numpy as np

from src.audio.models import Note, PitchFrame
from src.utils.converters import hz_to_midi, midi_to_note_name


def segment_notes(
    frames: list[PitchFrame],
    energy: np.ndarray | None = None,
    energy_threshold: float = 0.01,
    confidence_threshold: float = 0.5,
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
    note_energies: list[float] = []

    for i, frame in enumerate(frames):
        # Determinar si el frame es válido
        has_energy = True
        frame_energy = 0.0
        if energy is not None and i < len(energy):
            has_energy = energy[i] > energy_threshold
            frame_energy = float(energy[i])

        is_valid = frame.frequency > min_freq and frame.confidence >= confidence_threshold and has_energy

        if is_valid:
            midi_num = hz_to_midi(frame.frequency)

            if current_midi is None:
                # Iniciar nueva nota
                current_midi = midi_num
                note_start = frame.time
                note_freqs = [frame.frequency]
                note_confs = [frame.confidence]
                note_energies = [frame_energy]

            elif midi_num == current_midi:
                # Continuar nota actual
                note_freqs.append(frame.frequency)
                note_confs.append(frame.confidence)
                note_energies.append(frame_energy)

            else:
                # Cambio de nota: guardar anterior
                _maybe_add_note(
                    notes, current_midi, note_start, frame.time,
                    note_freqs, note_confs, note_energies,
                    min_note_duration, time_offset,
                )
                # Iniciar nueva
                current_midi = midi_num
                note_start = frame.time
                note_freqs = [frame.frequency]
                note_confs = [frame.confidence]
                note_energies = [frame_energy]
        else:
            # Silencio o ruido: cerrar nota actual
            if current_midi is not None:
                _maybe_add_note(
                    notes, current_midi, note_start, frame.time,
                    note_freqs, note_confs, note_energies,
                    min_note_duration, time_offset,
                )
                current_midi = None
                note_freqs = []
                note_confs = []
                note_energies = []

    # Cerrar última nota si existe
    if current_midi is not None and note_freqs:
        end_time = frames[-1].time + 0.01  # Agregar un frame más
        _maybe_add_note(
            notes, current_midi, note_start, end_time,
            note_freqs, note_confs, note_energies,
            min_note_duration, time_offset,
        )

    return notes


def _maybe_add_note(
    notes: list[Note],
    midi_number: int,
    start_time: float,
    end_time: float,
    frequencies: list[float],
    confidences: list[float],
    energies: list[float],
    min_duration: float,
    time_offset: float = 0.0,
) -> None:
    """Agrega una nota a la lista si cumple con la duración mínima."""
    duration = end_time - start_time
    if duration < min_duration or not frequencies:
        return

    avg_freq = sum(frequencies) / len(frequencies)
    avg_conf = sum(confidences) / len(confidences)
    avg_energy = sum(energies) / len(energies) if energies else None

    notes.append(
        Note(
            midi_number=midi_number,
            note_name=midi_to_note_name(midi_number),
            start_time=round(start_time + time_offset, 4),
            duration=round(duration, 4),
            frequency=round(avg_freq, 2),
            confidence=round(avg_conf, 3),
            energy=avg_energy if avg_energy and avg_energy > 0 else None,
        )
    )


def merge_same_pitch_notes(
    notes: list[Note],
    max_gap: float = 0.08,
) -> list[Note]:
    """
    Fusiona notas consecutivas con el mismo MIDI number separadas por gaps cortos.

    Gaps cortos (<=80ms) ocurren por consonantes, respiraciones breves o
    micro-silencios del detector. Fusionarlas produce una nota continua más natural.

    Args:
        notes: Lista de notas ordenadas por tiempo
        max_gap: Gap máximo en segundos para fusionar (default 80ms)

    Returns:
        Lista de notas fusionadas
    """
    if len(notes) <= 1:
        return notes

    merged: list[Note] = [notes[0]]

    for note in notes[1:]:
        prev = merged[-1]
        gap = note.start_time - prev.end_time

        if note.midi_number == prev.midi_number and 0 <= gap <= max_gap:
            # Fusionar: promediar freq/conf/energy ponderado por duración
            total_dur = prev.duration + note.duration + gap
            w_prev = prev.duration / total_dur
            w_note = note.duration / total_dur

            avg_freq = prev.frequency * w_prev + note.frequency * w_note
            avg_conf = prev.confidence * w_prev + note.confidence * w_note

            # Energy: promediar si ambas tienen, usar la que exista, o None
            avg_energy = None
            if prev.energy is not None and note.energy is not None:
                avg_energy = prev.energy * w_prev + note.energy * w_note
            elif prev.energy is not None:
                avg_energy = prev.energy
            elif note.energy is not None:
                avg_energy = note.energy

            merged[-1] = Note(
                midi_number=prev.midi_number,
                note_name=prev.note_name,
                start_time=prev.start_time,
                duration=round(total_dur, 4),
                frequency=round(avg_freq, 2),
                confidence=round(avg_conf, 3),
                energy=avg_energy,
            )
        else:
            merged.append(note)

    return merged


def refine_onsets(
    notes: list[Note],
    energy: np.ndarray,
    time_offset: float = 0.0,
    lookback_frames: int = 5,
    hop_seconds: float = 0.01,
) -> list[Note]:
    """
    Ajusta el inicio de cada nota al onset real de energía.

    Busca el máximo de la derivada de energía en los frames previos al start_time
    detectado. Esto captura el ataque real del sonido (transiente de energía).

    Args:
        notes: Lista de notas ordenadas por tiempo
        energy: Array de energía RMS por frame
        time_offset: Offset de tiempo aplicado a las notas
        lookback_frames: Cuántos frames antes buscar el onset (default 5 = 50ms)
        hop_seconds: Duración de cada frame en segundos (default 10ms)

    Returns:
        Lista de notas con start_time ajustado
    """
    if len(energy) == 0 or not notes:
        return notes

    # Derivada de energía (diferencias finitas)
    energy_diff = np.diff(energy, prepend=energy[0])

    refined: list[Note] = []

    for idx, note in enumerate(notes):
        # Convertir start_time a índice de frame
        note_time_raw = note.start_time - time_offset
        frame_idx = int(round(note_time_raw / hop_seconds))
        frame_idx = max(0, min(frame_idx, len(energy) - 1))

        # Buscar máximo de derivada en ventana de lookback
        search_start = max(0, frame_idx - lookback_frames)
        search_end = frame_idx + 1  # incluir frame actual

        if search_start < search_end and search_end <= len(energy_diff):
            window = energy_diff[search_start:search_end]
            onset_offset = np.argmax(window)
            onset_frame = search_start + onset_offset
            new_start = round(onset_frame * hop_seconds + time_offset, 4)

            # No solapar con nota anterior
            if idx > 0 and refined:
                prev_end = refined[-1].end_time
                new_start = max(new_start, prev_end)

            # Solo ajustar si el nuevo start es antes o igual al original
            if new_start <= note.start_time:
                new_duration = round(note.end_time - new_start, 4)
                if new_duration > 0:
                    refined.append(Note(
                        midi_number=note.midi_number,
                        note_name=note.note_name,
                        start_time=new_start,
                        duration=new_duration,
                        frequency=note.frequency,
                        confidence=note.confidence,
                        energy=note.energy,
                    ))
                    continue

        # Mantener nota original si no se pudo refinar
        refined.append(note)

    return refined


def filter_short_notes(
    notes: list[Note],
    min_duration: float = 0.06,
) -> list[Note]:
    """
    Elimina notas demasiado cortas que sobrevivieron al merge.

    Post-merge, las notas < 60ms son probablemente artefactos.

    Args:
        notes: Lista de notas
        min_duration: Duración mínima en segundos (default 60ms)

    Returns:
        Lista filtrada
    """
    return [n for n in notes if n.duration >= min_duration]
