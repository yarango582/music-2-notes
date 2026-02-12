"""Detección de pitch usando TorchCREPE."""

from typing import Literal

import numpy as np
import torch
import torchcrepe

from src.audio.models import PitchFrame


ModelSize = Literal["tiny", "full"]


def detect_pitches(
    audio: np.ndarray,
    sr: int,
    model_size: ModelSize = "tiny",
    device: str | None = None,
) -> list[PitchFrame]:
    """
    Detecta pitch frame a frame usando TorchCREPE.

    Args:
        audio: Array numpy de audio (mono, preferiblemente 16kHz)
        sr: Sample rate del audio
        model_size: Tamaño del modelo ('tiny' o 'full')
        device: Device de PyTorch (None = auto-detect)

    Returns:
        Lista de PitchFrame con tiempo, frecuencia y confianza
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # Preparar tensor
    audio_tensor = torch.from_numpy(audio).unsqueeze(0).to(device)

    # Ejecutar predicción con periodicity (confianza real del modelo)
    pitch, periodicity = torchcrepe.predict(
        audio_tensor,
        sample_rate=sr,
        model=model_size,
        batch_size=1,
        device=device,
        return_periodicity=True,
    )

    # Extraer resultados
    frequency = pitch[0].cpu()  # Shape: (n_frames,)
    confidence = periodicity[0].cpu()  # Shape: (n_frames,)
    n_frames = len(frequency)

    # Generar timestamps (10ms por frame, default de torchcrepe)
    hop_ms = 10.0
    timestamps = np.arange(n_frames) * (hop_ms / 1000.0)

    # Construir lista de PitchFrames con confianza real del modelo
    frames = []
    for i in range(n_frames):
        frames.append(
            PitchFrame(
                time=timestamps[i],
                frequency=max(frequency[i].item(), 0.0),
                confidence=confidence[i].item(),
            )
        )

    return frames
