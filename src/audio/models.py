"""
Modelos de datos para representar información de audio y notas musicales.
"""

from dataclasses import dataclass
from typing import Optional


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
        velocity: Velocidad MIDI (0-127), basada en confidence
    """

    midi_number: int
    note_name: str
    start_time: float
    duration: float
    frequency: float
    confidence: float
    velocity: Optional[int] = None

    def __post_init__(self):
        """Validar rangos y calcular velocity si no está especificada."""
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

        # Calcular velocity basado en confidence si no está especificado
        if self.velocity is None:
            # Mapear confidence (0-1) a velocity MIDI (50-127)
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
