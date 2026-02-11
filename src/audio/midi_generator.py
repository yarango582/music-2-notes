"""Generación de archivos MIDI a partir de notas detectadas."""

from pathlib import Path

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

from src.audio.models import Note


def generate_midi(
    notes: list[Note],
    output_path: str | Path,
    tempo: int = 120,
    ticks_per_beat: int = 480,
) -> Path:
    """
    Genera un archivo MIDI estándar con las notas detectadas.

    Usa delta time correcto para mantener el timing del audio original.

    Args:
        notes: Lista de notas detectadas
        output_path: Ruta donde guardar el archivo MIDI
        tempo: BPM del archivo MIDI (default: 120)
        ticks_per_beat: Resolución MIDI (default: 480)

    Returns:
        Path del archivo MIDI generado
    """
    output_path = Path(output_path)

    mid = MidiFile(ticks_per_beat=ticks_per_beat)
    track = MidiTrack()
    mid.tracks.append(track)

    # Tempo
    track.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo), time=0))

    # Crear eventos MIDI ordenados por tiempo
    events = []
    for note in notes:
        events.append({
            "time": note.start_time,
            "type": "note_on",
            "note": note.midi_number,
            "velocity": note.velocity,
        })
        events.append({
            "time": note.end_time,
            "type": "note_off",
            "note": note.midi_number,
            "velocity": 0,
        })

    events.sort(key=lambda x: (x["time"], x["type"] == "note_on"))

    # Convertir a delta ticks
    ticks_per_second = ticks_per_beat * (tempo / 60.0)
    last_tick = 0

    for event in events:
        absolute_tick = int(event["time"] * ticks_per_second)
        delta_tick = max(0, absolute_tick - last_tick)

        track.append(Message(
            event["type"],
            note=event["note"],
            velocity=event["velocity"],
            time=delta_tick,
        ))
        last_tick = absolute_tick

    mid.save(output_path)
    return output_path
