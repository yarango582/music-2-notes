"""
Utilidades para conversión entre frecuencias, notas MIDI y nombres de notas.
"""

import numpy as np


def hz_to_midi(frequency: float) -> int:
    """
    Convierte frecuencia en Hz a número de nota MIDI.

    Formula: MIDI = 69 + 12 * log2(frequency / 440)
    Donde 69 es A4 (440 Hz)

    Args:
        frequency: Frecuencia en Hz

    Returns:
        Número de nota MIDI (0-127)

    Example:
        >>> hz_to_midi(440.0)
        69  # A4
        >>> hz_to_midi(261.63)
        60  # C4
    """
    if frequency <= 0:
        raise ValueError(f"frequency debe ser > 0, recibido: {frequency}")

    midi = 69 + 12 * np.log2(frequency / 440.0)
    midi_number = int(round(midi))

    # Clamp a rango válido MIDI (0-127)
    return max(0, min(127, midi_number))


def midi_to_hz(midi_number: int) -> float:
    """
    Convierte número de nota MIDI a frecuencia en Hz.

    Formula: frequency = 440 * 2^((MIDI - 69) / 12)

    Args:
        midi_number: Número de nota MIDI (0-127)

    Returns:
        Frecuencia en Hz

    Example:
        >>> midi_to_hz(69)
        440.0  # A4
        >>> midi_to_hz(60)
        261.6255653005986  # C4
    """
    if not 0 <= midi_number <= 127:
        raise ValueError(
            f"midi_number debe estar entre 0 y 127, recibido: {midi_number}"
        )

    return 440.0 * (2.0 ** ((midi_number - 69) / 12.0))


def midi_to_note_name(midi_number: int) -> str:
    """
    Convierte número MIDI a nombre de nota con octava.

    Args:
        midi_number: Número de nota MIDI (0-127)

    Returns:
        Nombre de la nota (ej: "C4", "A#3", "Gb5")

    Example:
        >>> midi_to_note_name(60)
        'C4'
        >>> midi_to_note_name(69)
        'A4'
        >>> midi_to_note_name(70)
        'A#4'
    """
    if not 0 <= midi_number <= 127:
        raise ValueError(
            f"midi_number debe estar entre 0 y 127, recibido: {midi_number}"
        )

    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (midi_number // 12) - 1
    note = notes[midi_number % 12]

    return f"{note}{octave}"


def note_name_to_midi(note_name: str) -> int:
    """
    Convierte nombre de nota a número MIDI.

    Args:
        note_name: Nombre de la nota (ej: "C4", "A#3", "Bb5")

    Returns:
        Número de nota MIDI (0-127)

    Example:
        >>> note_name_to_midi("C4")
        60
        >>> note_name_to_midi("A4")
        69
        >>> note_name_to_midi("A#4")
        70
        >>> note_name_to_midi("Bb4")  # Enarmónico de A#4
        70
    """
    # Normalizar entrada
    note_name = note_name.strip().upper()

    # Mapa de notas a semitonos (C = 0)
    note_map = {
        "C": 0,
        "C#": 1,
        "DB": 1,
        "D": 2,
        "D#": 3,
        "EB": 3,
        "E": 4,
        "F": 5,
        "F#": 6,
        "GB": 6,
        "G": 7,
        "G#": 8,
        "AB": 8,
        "A": 9,
        "A#": 10,
        "BB": 10,
        "B": 11,
    }

    # Extraer nota y octava
    if len(note_name) == 2:  # Ej: "C4"
        note, octave_str = note_name[0], note_name[1]
    elif len(note_name) == 3:  # Ej: "C#4" o "Bb4"
        note, octave_str = note_name[:2], note_name[2]
    else:
        raise ValueError(f"Formato de nota inválido: {note_name}")

    if note not in note_map:
        raise ValueError(f"Nota no reconocida: {note}")

    try:
        octave = int(octave_str)
    except ValueError:
        raise ValueError(f"Octava inválida: {octave_str}")

    # Calcular MIDI number
    midi_number = (octave + 1) * 12 + note_map[note]

    if not 0 <= midi_number <= 127:
        raise ValueError(
            f"Nota fuera de rango MIDI: {note_name} (MIDI {midi_number})"
        )

    return midi_number
