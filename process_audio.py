#!/usr/bin/env python3
"""
Script para procesar archivos de audio reales.
Detecta pitch, genera notas y crea archivo MIDI.

Uso:
    python process_audio.py <archivo_audio>
    python process_audio.py tests/fixtures/audio/mi_cancion.wav
"""

import sys
import json
import argparse
from pathlib import Path
import numpy as np
import torch
import torchcrepe
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

# Importar módulos del proyecto
from src.audio.loader import load_audio, get_audio_info, AudioLoadError
from src.audio.models import Note
from src.utils.converters import hz_to_midi, midi_to_note_name


def process_audio_file(
    input_file: Path,
    model_size: str = "tiny",
    confidence_threshold: float = 0.5,
    device: str = "cpu",
) -> tuple[list[Note], dict]:
    """
    Procesa un archivo de audio y extrae notas musicales.

    Args:
        input_file: Ruta al archivo de audio
        model_size: Tamaño del modelo CREPE (tiny o full)
        confidence_threshold: Umbral mínimo de confianza (0-1)
        device: Device de PyTorch ('cpu' o 'cuda')

    Returns:
        Tuple de (lista de notas, metadata)
    """
    print(f"📂 Cargando: {input_file.name}")

    # 1. Obtener info del archivo
    try:
        info = get_audio_info(input_file)
        print(f"   ℹ️  Duración: {info['duration']:.2f}s")
        print(f"   ℹ️  Sample rate original: {info['sample_rate']} Hz")
        print(f"   ℹ️  Canales: {info['channels']}")
    except AudioLoadError as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)

    # 2. Cargar audio
    print(f"\n🎵 Cargando audio...")
    try:
        audio, sr = load_audio(input_file, target_sr=16000, mono=True)
        print(f"   ✓ Audio cargado: {len(audio)} samples @ {sr} Hz")
    except AudioLoadError as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)

    # 3. Detectar pitch con TorchCREPE
    # Modelos disponibles en torchcrepe: tiny (rápido) o full (preciso, lento)
    print(f"\n🔍 Detectando pitch con TorchCREPE (modelo: {model_size})...")
    print(f"   ℹ️  Device: {device}")
    if model_size == "full":
        print(f"   ⚠️  Modelo 'full' puede tardar varios minutos...")

    audio_tensor = torch.from_numpy(audio).unsqueeze(0)  # Shape: (1, samples)

    try:
        pitch = torchcrepe.predict(
            audio_tensor,
            sample_rate=sr,
            model=model_size,
            batch_size=1,
            device=device,
        )

        # Generar timestamps
        hop_length = int(sr * 0.01)  # 10ms por defecto
        n_frames = pitch.shape[1]
        time = torch.arange(n_frames) * 0.01  # 10ms por frame

        frequency = pitch[0]  # Extraer batch 0

        print(f"   ✓ {n_frames} frames detectados")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)

    # 4. Filtrar y segmentar notas
    print(f"\n🎼 Segmentando notas...")

    # Calcular amplitud del audio para filtrar mejor
    # Usar ventanas de audio para detectar actividad vocal real
    hop_samples = int(sr * 0.01)  # 10ms
    frame_energy = []

    for i in range(len(frequency)):
        start_sample = i * hop_samples
        end_sample = min(start_sample + hop_samples, len(audio))
        if end_sample > start_sample:
            frame_audio = audio[start_sample:end_sample]
            energy = np.sqrt(np.mean(frame_audio ** 2))  # RMS energy
            frame_energy.append(energy)
        else:
            frame_energy.append(0)

    frame_energy = np.array(frame_energy)

    # Threshold adaptivo: usar percentil para filtrar silencio
    energy_threshold = np.percentile(frame_energy, 25)  # 25% más bajo es silencio
    min_energy = max(energy_threshold, 0.01)  # Mínimo absoluto

    print(f"   ℹ️  Umbral de energía: {min_energy:.4f}")

    # Filtrar frecuencias válidas con energía suficiente
    notes = []
    current_midi = None
    note_start = None
    note_freqs = []
    min_freq = 80  # Hz mínimo (aprox. E2, por debajo es ruido)

    for i in range(len(time)):
        freq = frequency[i].item()
        energy = frame_energy[i] if i < len(frame_energy) else 0

        # Considerar válido si tiene frecuencia Y energía suficiente
        is_valid = freq > min_freq and energy > min_energy

        if is_valid:  # Frecuencia válida con energía
            midi_num = hz_to_midi(freq)

            if current_midi is None:
                # Iniciar nueva nota
                current_midi = midi_num
                note_start = time[i].item()
                note_freqs = [freq]
            elif midi_num == current_midi:
                # Continuar nota actual
                note_freqs.append(freq)
            else:
                # Cambio de nota: guardar anterior y empezar nueva
                if note_start is not None and len(note_freqs) > 0:
                    duration = time[i].item() - note_start
                    if duration >= 0.05:  # Mínimo 50ms
                        avg_freq = sum(note_freqs) / len(note_freqs)
                        note = Note(
                            midi_number=current_midi,
                            note_name=midi_to_note_name(current_midi),
                            start_time=note_start,
                            duration=duration,
                            frequency=avg_freq,
                            confidence=1.0,  # Simplificado
                        )
                        notes.append(note)

                # Nueva nota
                current_midi = midi_num
                note_start = time[i].item()
                note_freqs = [freq]
        else:
            # Silencio: terminar nota actual si existe
            if current_midi is not None and note_start is not None:
                duration = time[i].item() - note_start
                if duration >= 0.05:
                    avg_freq = sum(note_freqs) / len(note_freqs)
                    note = Note(
                        midi_number=current_midi,
                        note_name=midi_to_note_name(current_midi),
                        start_time=note_start,
                        duration=duration,
                        frequency=avg_freq,
                        confidence=1.0,
                    )
                    notes.append(note)

            current_midi = None
            note_start = None
            note_freqs = []

    # Guardar última nota si existe
    if current_midi is not None and note_start is not None and len(note_freqs) > 0:
        duration = time[-1].item() - note_start
        if duration >= 0.05:
            avg_freq = sum(note_freqs) / len(note_freqs)
            note = Note(
                midi_number=current_midi,
                note_name=midi_to_note_name(current_midi),
                start_time=note_start,
                duration=duration,
                frequency=avg_freq,
                confidence=1.0,
            )
            notes.append(note)

    total_frames = len(time)
    valid_frames = sum(1 for i in range(len(time)) if i < len(frame_energy) and frame_energy[i] > min_energy and frequency[i].item() > min_freq)

    print(f"   ✓ {len(notes)} notas detectadas")
    print(f"   ℹ️  Frames procesados: {total_frames}")
    print(f"   ℹ️  Frames válidos (con energía): {valid_frames} ({valid_frames/total_frames*100:.1f}%)")

    # Metadata
    metadata = {
        "input_file": str(input_file),
        "audio_duration": info["duration"],
        "sample_rate": sr,
        "model_size": model_size,
        "confidence_threshold": confidence_threshold,
        "notes_detected": len(notes),
    }

    return notes, metadata


def generate_midi(notes: list[Note], output_path: Path, tempo: int = 120) -> None:
    """
    Genera archivo MIDI desde lista de notas con timing correcto.

    El timing en MIDI usa 'delta time' (tiempo desde el evento anterior),
    no tiempo absoluto. Esto mantiene el tempo original del audio.
    """
    mid = MidiFile(ticks_per_beat=480)  # Standard MIDI resolution
    track = MidiTrack()
    mid.tracks.append(track)

    # Tempo en microsegundos por beat
    track.append(MetaMessage("set_tempo", tempo=mido.bpm2tempo(tempo), time=0))

    # Crear lista de eventos MIDI (note_on y note_off) con timestamps absolutos
    events = []

    for note in notes:
        # Evento Note ON
        events.append(
            {
                "time": note.start_time,
                "type": "note_on",
                "note": note.midi_number,
                "velocity": note.velocity,
            }
        )

        # Evento Note OFF
        events.append(
            {
                "time": note.end_time,
                "type": "note_off",
                "note": note.midi_number,
                "velocity": 0,
            }
        )

    # Ordenar eventos por tiempo
    events.sort(key=lambda x: x["time"])

    # Convertir timestamps absolutos (segundos) a delta ticks
    # Formula: ticks = segundos * ticks_per_beat * (BPM / 60)
    ticks_per_second = mid.ticks_per_beat * (tempo / 60.0)

    last_tick = 0
    for event in events:
        # Convertir tiempo absoluto a ticks
        absolute_tick = int(event["time"] * ticks_per_second)

        # Calcular delta (tiempo desde último evento)
        delta_tick = absolute_tick - last_tick
        delta_tick = max(0, delta_tick)  # Asegurar no negativo

        # Agregar mensaje MIDI con delta time
        if event["type"] == "note_on":
            track.append(
                Message(
                    "note_on",
                    note=event["note"],
                    velocity=event["velocity"],
                    time=delta_tick,
                )
            )
        else:  # note_off
            track.append(
                Message(
                    "note_off",
                    note=event["note"],
                    velocity=event["velocity"],
                    time=delta_tick,
                )
            )

        last_tick = absolute_tick

    mid.save(output_path)
    print(f"   ✓ MIDI guardado: {output_path}")


def main():
    """Función principal."""
    print("=" * 60)
    print("🎵 Music-2-Notes - Procesador de Audio")
    print("=" * 60)
    print()

    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description="Procesa audio vocal y genera MIDI con detección de notas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Procesamiento rápido (tiny)
  python process_audio.py tests/fixtures/audio/song.wav

  # Procesamiento preciso (full)
  python process_audio.py tests/fixtures/audio/song.wav --model full

Modelos disponibles:
  tiny - Rápido, menos preciso (recomendado para pruebas)
  full - Preciso, muy lento (mejor calidad)
        """,
    )

    parser.add_argument("input_file", type=str, help="Archivo de audio a procesar")
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        choices=["tiny", "full"],
        default="tiny",
        help="Modelo de TorchCREPE a usar (default: tiny)",
    )

    args = parser.parse_args()
    input_file = Path(args.input_file)

    if not input_file.exists():
        print(f"❌ Archivo no encontrado: {input_file}")
        sys.exit(1)

    # Determinar device
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Procesar audio
    notes, metadata = process_audio_file(
        input_file, model_size=args.model, device=device
    )

    if len(notes) == 0:
        print("\n⚠️  No se detectaron notas en el audio.")
        sys.exit(0)

    # Crear carpeta output si no existe
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Nombres de archivos de salida
    stem = input_file.stem
    midi_path = output_dir / f"{stem}.mid"
    json_path = output_dir / f"{stem}.json"

    # Generar MIDI
    print(f"\n💾 Generando outputs...")
    generate_midi(notes, midi_path, tempo=120)

    # Generar JSON
    output_data = {
        "metadata": metadata,
        "notes": [note.to_dict() for note in notes],
    }

    with open(json_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"   ✓ JSON guardado: {json_path}")

    # Resumen
    print()
    print("=" * 60)
    print("✅ PROCESAMIENTO COMPLETADO")
    print("=" * 60)
    print()
    print(f"📊 Resumen:")
    print(f"   • Archivo: {input_file.name}")
    print(f"   • Duración: {metadata['audio_duration']:.2f}s")
    print(f"   • Notas detectadas: {len(notes)}")
    print()
    print(f"📁 Outputs:")
    print(f"   • MIDI: {midi_path}")
    print(f"   • JSON: {json_path}")
    print()
    print("💡 Prueba el MIDI en tu DAW favorito!")
    print()


if __name__ == "__main__":
    main()
