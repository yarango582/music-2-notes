"""Configuración centralizada del sistema."""

from pathlib import Path
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # General
    ENV: str = "development"
    SECRET_KEY: str = "change-this-in-production"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "*"

    # Database (SQLite por defecto, 0 costo)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'music2notes.db'}"

    # Storage
    STORAGE_PATH: str = str(BASE_DIR / "storage")

    # Audio processing
    DEFAULT_MODEL_SIZE: str = "tiny"
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.5
    DEFAULT_MIN_NOTE_DURATION: float = 0.05
    MAX_AUDIO_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_AUDIO_DURATION: float = 600  # 10 minutos

    # TorchCREPE
    CREPE_BATCH_SIZE: int = 512
    CREPE_FMIN: float = 65.0     # C2
    CREPE_FMAX: float = 1047.0   # C6

    # Pitch post-processing
    PITCH_MEDIAN_WINDOW: int = 5           # frames (50ms)
    VIBRATO_SMOOTH_WINDOW: int = 13        # frames (130ms, ~1 ciclo a 8Hz)
    VIBRATO_EXTENT_CENTS: float = 120.0    # threshold peak-to-peak

    # Note post-processing
    NOTE_MERGE_MAX_GAP: float = 0.08       # segundos
    POST_MERGE_MIN_DURATION: float = 0.06  # segundos
    ONSET_LOOKBACK_FRAMES: int = 5         # frames (50ms)

    # Velocity (RMS → MIDI)
    VELOCITY_MIN: int = 30
    VELOCITY_MAX: int = 120
    VELOCITY_DB_MIN: float = -46.0
    VELOCITY_DB_MAX: float = -6.0

    # Webhooks
    WEBHOOK_TIMEOUT: int = 30
    WEBHOOK_MAX_RETRIES: int = 5
    WEBHOOK_SECRET_KEY: str = "webhook-secret-change-this"

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
