# Music-2-Notes

Sistema de analisis vocal que detecta notas musicales en audio y genera MIDI + JSON. Usa el modelo CREPE (deep learning) para pitch detection preciso y una API REST asincrona con sistema de jobs.

## Stack

- **Pitch Detection**: TorchCREPE (CNN pre-entrenado, modelos `tiny` y `full`)
- **API**: FastAPI + Uvicorn
- **Database**: SQLite + aiosqlite (zero cost, sin servidor externo)
- **Audio**: librosa, soundfile, ffmpeg
- **MIDI**: mido
- **Jobs**: asyncio background tasks (sin Celery/Redis)

## Arquitectura

```
Cliente --> FastAPI --> asyncio.to_thread() --> TorchCREPE (CPU)
               |                                    |
            SQLite                           MIDI + JSON
               |                                    |
          Job status                          Storage local
               |
          Webhook (opcional)
```

## Quick Start

```bash
# Clonar
git clone https://github.com/your-org/music-2-notes.git
cd music-2-notes

# Entorno virtual
python -m venv .venv
source .venv/bin/activate        # Bash/Zsh
source .venv/bin/activate.fish   # Fish

# Dependencias
pip install -e .

# Configurar
cp .env.example .env

# Ejecutar API
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Docs interactivos en http://localhost:8000/docs

## CLI (sin API)

```bash
# Procesamiento rapido
python process_audio.py tests/fixtures/audio/song.wav

# Modelo preciso
python process_audio.py song.wav --model full

# Ajustar confianza
python process_audio.py song.wav --confidence 0.9
```

Los resultados se guardan en `output/` (MIDI + JSON).

## API

### Crear job

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "audio_file=@vocal.wav" \
  -F "model_size=tiny" \
  -F "confidence_threshold=0.95"
```

Response (202):
```json
{
  "job_id": "uuid",
  "status": "pending",
  "created_at": "2026-02-10T20:00:00"
}
```

### Consultar estado

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

### Descargar resultados

```bash
# MIDI
curl http://localhost:8000/api/v1/jobs/{job_id}/download/midi -o result.mid

# JSON con notas
curl http://localhost:8000/api/v1/jobs/{job_id}/download/json -o result.json

# Resultado completo
curl http://localhost:8000/api/v1/jobs/{job_id}/result
```

### Webhooks

Notificacion automatica al completar:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "audio_file=@vocal.wav" \
  -F "webhook_url=https://tu-dominio.com/webhook"
```

### Health check

```bash
curl http://localhost:8000/api/v1/health
```

## Estructura

```
music-2-notes/
├── src/
│   ├── api/              # FastAPI endpoints
│   │   ├── v1/           # Routes: jobs, health
│   │   └── models/       # Pydantic request/response
│   ├── audio/            # Pipeline de audio
│   │   ├── loader.py         # Carga y resampling
│   │   ├── preprocessor.py   # Normalizacion y energia
│   │   ├── pitch_detector.py # TorchCREPE inference + periodicity
│   │   ├── note_segmenter.py # Frames -> notas musicales
│   │   ├── midi_generator.py # Notas -> MIDI
│   │   ├── json_formatter.py # Notas -> JSON
│   │   └── models.py         # PitchFrame, Note dataclasses
│   ├── workers/          # Background job processing (asyncio)
│   ├── db/               # SQLite models y repositorios
│   ├── core/             # Config, exceptions, security
│   ├── storage/          # File storage local
│   └── utils/            # Hz->MIDI converters
├── process_audio.py      # CLI standalone
├── Dockerfile            # Multi-stage, CPU-only torch
├── docs/DEPLOY.md        # Guia de despliegue
└── tests/fixtures/audio/ # Audio de prueba
```

## Docker

```bash
docker build -t music2notes .
docker run -p 8000:8000 -v music2notes_data:/app/data music2notes
```

La imagen usa multi-stage build con PyTorch CPU-only (~1.5GB vs ~8GB con CUDA).

## Despliegue

Ver [docs/DEPLOY.md](docs/DEPLOY.md) para opciones con costo $0:

| Plataforma    | RAM    | Costo  | Persistencia |
|--------------|--------|--------|-------------|
| Fly.io       | 512 MB | $0/mes | Si (volumen)|
| Railway      | 512 MB | $0-5   | Limitada    |
| Render       | 512 MB | $0/mes | No          |
| Oracle Cloud | 4 GB   | $0/mes | Si          |

## Modelo CREPE

Usa [TorchCREPE](https://github.com/maxrmorrison/torchcrepe), implementacion PyTorch del modelo CREPE para pitch detection monofonico.

- **tiny**: Rapido (~50ms/s audio), bueno para pruebas
- **full**: Maxima precision (~1s/s audio), recomendado para produccion

Confianza por defecto: **0.95** (95%). El modelo retorna periodicity real por frame, filtrando notas donde CREPE tiene baja certeza.

## Licencia

MIT
