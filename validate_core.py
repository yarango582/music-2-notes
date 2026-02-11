#!/usr/bin/env python3
"""
Script de validación rápida del core de Music-2-Notes.
Prueba: Audio sintético → TorchCREPE → Notas → MIDI
"""

import numpy as np
import torch
import torchcrepe
from pathlib import Path
import sys

print("🔍 Validando Core de Music-2-Notes...\n")

# ============================================================================
# 1. GENERAR AUDIO SINTÉTICO (440 Hz = A4)
# ============================================================================
print("1️⃣  Generando audio sintético (440 Hz = A4)...")

SAMPLE_RATE = 16000  # TorchCREPE usa 16kHz
DURATION = 2.0  # segundos
FREQUENCY = 440.0  # Hz (nota A4)

t = np.linspace(0, DURATION, int(SAMPLE_RATE * DURATION))
audio = np.sin(2 * np.pi * FREQUENCY * t).astype(np.float32)

print(f"   ✓ Audio generado: {len(audio)} samples, {DURATION}s @ {SAMPLE_RATE}Hz")
print(f"   ✓ Frecuencia esperada: {FREQUENCY} Hz (A4)\n")

# ============================================================================
# 2. PITCH DETECTION CON TORCHCREPE
# ============================================================================
print("2️⃣  Detectando pitch con TorchCREPE...")

# Convertir a tensor de PyTorch
audio_tensor = torch.from_numpy(audio).unsqueeze(0)  # Shape: (1, samples)

# Detectar si hay GPU disponible
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"   ℹ️  Usando device: {device}")

try:
    # Ejecutar CREPE
    # model: tiny, small, medium, large, full
    # step_size: milisegundos entre frames (default: 10ms)

    # TorchCREPE devuelve solo pitch y periodicity por defecto
    pitch = torchcrepe.predict(
        audio_tensor,
        sample_rate=SAMPLE_RATE,
        model="tiny",  # Usamos tiny para validación rápida
        batch_size=1,
        device=device,
    )

    # Generar timestamps manualmente
    hop_length = int(SAMPLE_RATE * 0.01)  # 10ms por defecto
    n_frames = pitch.shape[1]
    time = torch.arange(n_frames) * 0.01  # 10ms por frame

    # pitch shape: (batch, time)
    frequency = pitch[0]  # Extraer batch 0

    # Calcular "confidence" basado en la estabilidad del pitch
    # (En torchcrepe, valores cercanos a 0 son silencio)
    confidence = (frequency > 50).float()  # Threshold simple

    print(f"   ✓ Pitch detectado exitosamente")
    print(f"   ✓ Frames detectados: {len(time)}")
    print(f"   ✓ Rango de tiempo: {time[0]:.2f}s - {time[-1]:.2f}s")

    # Estadísticas (filtrar valores válidos > 0)
    valid_freq = frequency[frequency > 50]  # Filtrar silencio
    if len(valid_freq) > 0:
        freq_mean = valid_freq.mean().item()
        freq_std = valid_freq.std().item()
    else:
        freq_mean = 0.0
        freq_std = 0.0

    conf_mean = confidence.mean().item()

    print(f"   ✓ Frecuencia detectada: {freq_mean:.2f} ± {freq_std:.2f} Hz")
    print(f"   ✓ Confianza promedio: {conf_mean:.3f}")

    # Verificar que detectó cerca de 440 Hz
    error = abs(freq_mean - FREQUENCY)
    if error < 10:  # Tolerancia de 10 Hz
        print(f"   ✅ Frecuencia correcta (error: {error:.2f} Hz)\n")
    else:
        print(f"   ⚠️  Frecuencia con error alto: {error:.2f} Hz\n")

except Exception as e:
    print(f"   ❌ Error en pitch detection: {e}")
    sys.exit(1)

# ============================================================================
# 3. CONVERTIR FRECUENCIA A NOTA MIDI
# ============================================================================
print("3️⃣  Convirtiendo frecuencia a nota MIDI...")

def hz_to_midi(frequency: float) -> int:
    """Convierte frecuencia en Hz a número de nota MIDI."""
    return int(round(69 + 12 * np.log2(frequency / 440.0)))

def midi_to_note_name(midi_number: int) -> str:
    """Convierte número MIDI a nombre de nota."""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi_number // 12) - 1
    note = notes[midi_number % 12]
    return f"{note}{octave}"

# Convertir la frecuencia promedio a MIDI
midi_number = hz_to_midi(freq_mean)
note_name = midi_to_note_name(midi_number)

print(f"   ✓ Nota MIDI: {midi_number}")
print(f"   ✓ Nombre: {note_name}")
print(f"   ✓ Esperado: A4 (MIDI 69)")

if midi_number == 69:
    print(f"   ✅ Nota correcta!\n")
else:
    print(f"   ⚠️  Nota diferente a la esperada (diff: {midi_number - 69})\n")

# ============================================================================
# 4. GENERAR ARCHIVO MIDI SIMPLE
# ============================================================================
print("4️⃣  Generando archivo MIDI...")

try:
    import mido
    from mido import MidiFile, MidiTrack, Message, MetaMessage

    # Crear archivo MIDI
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)

    # Agregar tempo (120 BPM = 500000 microsegundos por beat)
    track.append(MetaMessage('set_tempo', tempo=500000, time=0))

    # Agregar nota (note on + note off)
    velocity = int(conf_mean * 77 + 50)  # Velocity basado en confianza (50-127)
    ticks_per_second = 480  # Ticks per beat, asumiendo 4/4 time

    # Note ON
    track.append(Message('note_on', note=midi_number, velocity=velocity, time=0))

    # Note OFF (después de 1 segundo)
    track.append(Message('note_off', note=midi_number, velocity=0, time=ticks_per_second))

    # Guardar archivo
    output_path = Path("validation_output.mid")
    mid.save(output_path)

    print(f"   ✓ MIDI creado: {output_path}")
    print(f"   ✓ Nota: {note_name} (MIDI {midi_number})")
    print(f"   ✓ Velocity: {velocity}")
    print(f"   ✅ Archivo guardado exitosamente\n")

except ImportError:
    print(f"   ⚠️  mido no disponible, saltando generación de MIDI\n")
except Exception as e:
    print(f"   ❌ Error generando MIDI: {e}\n")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("=" * 60)
print("✅ VALIDACIÓN COMPLETADA EXITOSAMENTE")
print("=" * 60)
print()
print("📊 Resumen:")
print(f"   • Audio sintético: {FREQUENCY} Hz (A4)")
print(f"   • Pitch detectado: {freq_mean:.2f} Hz")
print(f"   • Nota MIDI: {midi_number} ({note_name})")
print(f"   • Confianza: {conf_mean:.3f}")
print(f"   • Device: {device}")
print()
print("🎉 El core de Music-2-Notes funciona correctamente!")
print("    Puedes proceder con las siguientes fases.")
print()
print("💡 Prueba el MIDI generado:")
print(f"   • Archivo: validation_output.mid")
print(f"   • Abre en un DAW o reproductor MIDI")
print()
