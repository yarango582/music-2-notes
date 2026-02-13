"""Detección de pitch usando TorchCREPE."""

from typing import Literal

import numpy as np
import torch
import torchcrepe
import torchcrepe.decode

from src.audio.models import PitchFrame


ModelSize = Literal["tiny", "full"]


def detect_pitches(
    audio: np.ndarray,
    sr: int,
    model_size: ModelSize = "tiny",
    device: str | None = None,
    batch_size: int = 512,
    fmin: float = 65.0,
    fmax: float = 1047.0,
) -> list[PitchFrame]:
    """
    Detecta pitch frame a frame usando TorchCREPE.

    Args:
        audio: Array numpy de audio (mono, preferiblemente 16kHz)
        sr: Sample rate del audio
        model_size: Tamaño del modelo ('tiny' o 'full')
        device: Device de PyTorch (None = auto-detect)
        batch_size: Batch size para inferencia (512 óptimo para GPU)
        fmin: Frecuencia mínima en Hz (65 = C2)
        fmax: Frecuencia máxima en Hz (1047 = C6)

    Returns:
        Lista de PitchFrame con tiempo, frecuencia y confianza
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # Preparar tensor
    audio_tensor = torch.from_numpy(audio).unsqueeze(0).to(device)

    # Ejecutar predicción con Viterbi decoding y rango vocal
    pitch, periodicity = torchcrepe.predict(
        audio_tensor,
        sample_rate=sr,
        model=model_size,
        batch_size=batch_size,
        device=device,
        return_periodicity=True,
        decoder=torchcrepe.decode.viterbi,
        fmin=fmin,
        fmax=fmax,
    )

    # Extraer resultados como numpy arrays
    freq_np = pitch[0].cpu().numpy()
    conf_np = periodicity[0].cpu().numpy()
    n_frames = len(freq_np)

    # Clamp frecuencias negativas
    freq_np = np.maximum(freq_np, 0.0)

    # Timestamps (10ms por frame, default torchcrepe)
    hop_ms = 10.0
    timestamps = np.arange(n_frames) * (hop_ms / 1000.0)

    # Construir PitchFrames vectorizado
    frames = [
        PitchFrame(
            time=timestamps[i],
            frequency=float(freq_np[i]),
            confidence=float(conf_np[i]),
        )
        for i in range(n_frames)
    ]

    return frames
