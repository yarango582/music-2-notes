"""
Modelos de datos para representar información de audio y notas musicales.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np


def _energy_to_velocity(
    energy: float,
    min_vel: int = 30,
    max_vel: int = 120,
    db_min: float = -46.0,
    db_max: float = -6.0,
) -> int:
    """
    Mapea RMS energy a MIDI velocity usando escala logarítmica (dB).

    La percepción humana de volumen es logarítmica. Rango típico de voz
    normalizada: -46 dB (pianissimo) a -6 dB (fortissimo).
    """
    if energy <= 0:
        return min_vel

    db = 20.0 * np.log10(max(energy, 1e-10))
    normalized = (db - db_min) / (db_max - db_min)
    normalized = max(0.0, min(1.0, normalized))

    velocity = int(min_vel + normalized * (max_vel - min_vel))
    return max(0, min(127, velocity))


@dataclass
class PitchFrame:
    """
    Representa un frame individual de detección de pitch.

    Attributes:
        time: Timestamp en segundos desde el inicio del audio
        frequency: Frecuencia detectada en Hz
        confidence: Nivel de confianza de la detección (0.0 - 1.0)
    """

    time: float
    frequency: float
    confidence: float

    def __post_init__(self):
        """Validar rangos."""
        if self.time < 0:
            raise ValueError(f"time debe ser >= 0, recibido: {self.time}")
        if self.frequency < 0:
            raise ValueError(f"frequency debe ser >= 0, recibido: {self.frequency}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence debe estar entre 0 y 1, recibido: {self.confidence}"
            )


@dataclass
class Note:
    """
    Representa una nota musical detectada en el audio.

    Attributes:
        midi_number: Número de nota MIDI (0-127)
        note_name: Nombre de la nota (ej: "C4", "A#3")
        start_time: Tiempo de inicio en segundos
        duration: Duración de la nota en segundos
        frequency: Frecuencia promedio en Hz
        confidence: Nivel de confianza promedio (0.0 - 1.0)
        velocity: Velocidad MIDI (0-127)
        energy: Energía RMS promedio (uso interno, no se serializa)
    """

    midi_number: int
    note_name: str
    start_time: float
    duration: float
    frequency: float
    confidence: float
    velocity: Optional[int] = None
    energy: Optional[float] = None

    def __post_init__(self):
        """Validar rangos y calcular velocity."""
        if not 0 <= self.midi_number <= 127:
            raise ValueError(
                f"midi_number debe estar entre 0 y 127, recibido: {self.midi_number}"
            )
        if self.start_time < 0:
            raise ValueError(f"start_time debe ser >= 0, recibido: {self.start_time}")
        if self.duration <= 0:
            raise ValueError(f"duration debe ser > 0, recibido: {self.duration}")
        if self.frequency <= 0:
            raise ValueError(f"frequency debe ser > 0, recibido: {self.frequency}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence debe estar entre 0 y 1, recibido: {self.confidence}"
            )

        # Calcular velocity: preferir energia RMS, fallback a confidence
        if self.velocity is None:
            if self.energy is not None and self.energy > 0:
                self.velocity = _energy_to_velocity(self.energy)
            else:
                self.velocity = int(self.confidence * 77 + 50)

        if not 0 <= self.velocity <= 127:
            raise ValueError(
                f"velocity debe estar entre 0 y 127, recibido: {self.velocity}"
            )

    @property
    def end_time(self) -> float:
        """Calcula el tiempo de fin de la nota."""
        return self.start_time + self.duration

    def to_dict(self) -> dict:
        """Convierte la nota a diccionario para serialización."""
        return {
            "midi_number": self.midi_number,
            "note_name": self.note_name,
            "start_time": self.start_time,
            "duration": self.duration,
            "end_time": self.end_time,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "velocity": self.velocity,
        }
