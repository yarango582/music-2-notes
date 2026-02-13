#!/usr/bin/env python3
"""
CLI para procesar archivos de audio.
Detecta pitch vocal, genera notas musicales, exporta MIDI y JSON.

Uso:
    python process_audio.py <archivo_audio>
    python process_audio.py tests/fixtures/audio/mi_cancion.wav
    python process_audio.py song.wav --model full --confidence 0.9
"""

import sys
import json
import argparse
from pathlib import Path

import torch

from src.audio.loader import load_audio, get_audio_info, AudioLoadError
from src.audio.preprocessor import preprocess_audio, compute_frame_energy, compute_energy_threshold
from src.audio.pitch_detector import detect_pitches
from src.audio.pitch_post_processor import post_process_pitch
from src.audio.note_segmenter import (
    segment_notes, merge_same_pitch_notes, refine_onsets, filter_short_notes,
)
from src.audio.midi_generator import generate_midi
from src.audio.json_formatter import format_result
from src.core.config import settings


def main():
    parser = argparse.ArgumentParser(
        description="Procesa audio vocal y genera MIDI con deteccion de notas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python process_audio.py tests/fixtures/audio/song.wav
  python process_audio.py song.wav --model full
  python process_audio.py song.wav --confidence 0.9

Modelos disponibles:
  tiny - Rapido, menos preciso (recomendado para pruebas)
  full - Preciso, muy lento (mejor calidad)
        """,
    )
    parser.add_argument("input_file", type=str, help="Archivo de audio a procesar")
    parser.add_argument(
        "--model", "-m", type=str, choices=["tiny", "full"],
        default="tiny", help="Modelo TorchCREPE (default: tiny)",
    )
    parser.add_argument(
        "--confidence", "-c", type=float, default=0.5,
        help="Umbral de confianza 0-1 (default: 0.5)",
    )

    args = parser.parse_args()
    input_file = Path(args.input_file)

    if not input_file.exists():
        print(f"Archivo no encontrado: {input_file}")
        sys.exit(1)

    print("=" * 60)
    print("Music-2-Notes - Procesador de Audio")
    print("=" * 60)

    # 1. Info del audio
    try:
        info = get_audio_info(input_file)
        print(f"\nArchivo: {input_file.name}")
        print(f"Duracion: {info['duration']:.2f}s | SR: {info['sample_rate']} Hz | Canales: {info['channels']}")
    except AudioLoadError as e:
        print(f"Error cargando audio: {e}")
        sys.exit(1)

    # 2. Cargar y preprocesar
    audio, sr = load_audio(input_file, target_sr=16000, mono=True)
    audio, trim_offset = preprocess_audio(audio, sr)
    print(f"Audio cargado: {len(audio)} samples @ {sr} Hz")
    if trim_offset > 0:
        print(f"  Silencio inicial recortado: {trim_offset:.2f}s (offset aplicado a timestamps)")

    # 3. Detectar pitch con confianza real del modelo
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nDetectando pitch (modelo: {args.model}, device: {device})...")
    if args.model == "full":
        print("  Modelo 'full' puede tardar varios minutos...")

    frames = detect_pitches(
        audio, sr, model_size=args.model, device=device,
        batch_size=settings.CREPE_BATCH_SIZE,
        fmin=settings.CREPE_FMIN,
        fmax=settings.CREPE_FMAX,
    )
    print(f"  {len(frames)} frames detectados")

    # 4. Post-procesar pitch (filtro mediano + suavizado vibrato)
    frames = post_process_pitch(
        frames,
        median_window=settings.PITCH_MEDIAN_WINDOW,
        vibrato_smooth_window=settings.VIBRATO_SMOOTH_WINDOW,
        vibrato_extent_cents=settings.VIBRATO_EXTENT_CENTS,
    )
    print(f"  Pitch post-procesado (median={settings.PITCH_MEDIAN_WINDOW}, vibrato={settings.VIBRATO_SMOOTH_WINDOW})")

    # 5. Segmentar notas con filtrado de energia y confianza
    energy = compute_frame_energy(audio, sr)
    threshold = compute_energy_threshold(energy)
    notes = segment_notes(
        frames, energy=energy, energy_threshold=threshold,
        confidence_threshold=args.confidence,
        time_offset=trim_offset,
    )
    print(f"  {len(notes)} notas segmentadas (confianza >= {args.confidence})")

    # 6. Post-procesar notas: merge + onset refinement + filter
    notes = merge_same_pitch_notes(notes, max_gap=settings.NOTE_MERGE_MAX_GAP)
    notes = refine_onsets(
        notes, energy=energy, time_offset=trim_offset,
        lookback_frames=settings.ONSET_LOOKBACK_FRAMES,
    )
    notes = filter_short_notes(notes, min_duration=settings.POST_MERGE_MIN_DURATION)
    print(f"  {len(notes)} notas finales (post merge+onset+filter)")

    if not notes:
        print("\nNo se detectaron notas en el audio.")
        sys.exit(0)

    # 5. Generar outputs
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    stem = input_file.stem

    midi_path = generate_midi(notes, output_dir / f"{stem}.mid")
    print(f"\nMIDI: {midi_path}")

    result_data = format_result(
        notes=notes,
        audio_duration=info["duration"],
        model_size=args.model,
        confidence_threshold=args.confidence,
        input_file=input_file.name,
    )
    json_path = output_dir / f"{stem}.json"
    with open(json_path, "w") as f:
        json.dump(result_data, f, indent=2)
    print(f"JSON: {json_path}")

    # Resumen
    print(f"\n{'=' * 60}")
    print(f"Notas detectadas: {len(notes)}")
    print(f"Duracion audio: {info['duration']:.2f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
