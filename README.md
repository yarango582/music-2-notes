# Music-2-Notes 🎵→🎼

Sistema completo de análisis de pitch vocal con detección de notas musicales, generación de MIDI, y API REST asíncrona con webhooks.

## 🎯 Características

- **Pitch Detection con CREPE**: Modelo de deep learning pre-entrenado para detección precisa de pitch monofónico
- **Generación de MIDI**: Convierte audio vocal a archivos MIDI estándar
- **Export JSON**: Información detallada de notas con timing, duración, frecuencia y confianza
- **API REST Asíncrona**: Procesamiento en background con jobs y sistema de colas
- **Webhooks**: Notificaciones automáticas cuando el procesamiento completa
- **Arquitectura Escalable**: Celery workers, PostgreSQL, Redis

## 🏗️ Arquitectura

```
Cliente → FastAPI → Redis Queue → Celery Workers → PostgreSQL
                                       ↓
                              CREPE Model (Audio Processing)
                                       ↓
                              MIDI + JSON Output
                                       ↓
                              Webhook Notification
```

### Stack Tecnológico

- **API**: FastAPI + Uvicorn
- **Audio Processing**: librosa, CREPE, soundfile
- **MIDI**: mido
- **Job Queue**: Celery + Redis
- **Database**: PostgreSQL + SQLAlchemy
- **Testing**: pytest + pytest-asyncio

## 📋 Prerequisitos

- Python 3.10 o superior
- Docker y Docker Compose
- Git

## 🚀 Quick Start

### 1. Clonar el repositorio

```bash
git clone https://github.com/your-org/music-2-notes.git
cd music-2-notes
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

### 3. Crear virtual environment

```bash
python3.10 -m venv venv

# Activar venv:
# - Bash/Zsh:
source venv/bin/activate

# - Fish (CachyOS/Arch Linux):
source venv/bin/activate.fish

# - Windows:
# venv\Scripts\activate
```

### 4. Instalar dependencias

```bash
pip install -e ".[dev]"
```

### 5. Levantar servicios de infraestructura

```bash
docker-compose up -d postgres redis
```

### 6. Inicializar base de datos

```bash
# Crear migraciones
alembic upgrade head
```

### 7. Ejecutar la aplicación

**Terminal 1 - API:**
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
celery -A src.workers.celery_app worker --loglevel=info --concurrency=2
```

**Terminal 3 - Flower (opcional, para monitoreo):**
```bash
celery -A src.workers.celery_app flower --port=5555
```

## 📖 Uso

### API Endpoints

#### Crear un Job de Análisis

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "audio_file=@path/to/vocal.wav" \
  -F "model_size=medium" \
  -F "confidence_threshold=0.5"
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "created_at": "2026-02-10T20:00:00Z"
}
```

#### Consultar Estado de Job

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing",
  "progress": 65,
  "created_at": "2026-02-10T20:00:00Z",
  "started_at": "2026-02-10T20:00:05Z"
}
```

#### Obtener Resultado

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}/result
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "result": {
    "audio_duration": 120.5,
    "notes_detected": 487,
    "notes": [
      {
        "midi_number": 60,
        "note_name": "C4",
        "start_time": 0.5,
        "duration": 0.3,
        "frequency": 261.63,
        "confidence": 0.87
      }
    ],
    "files": {
      "midi": "url-to-midi",
      "json": "url-to-json"
    }
  }
}
```

#### Descargar MIDI

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}/download/midi -o result.mid
```

### Webhooks

Para recibir notificaciones automáticas cuando el job complete:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "audio_file=@vocal.wav" \
  -F "webhook_url=https://your-domain.com/webhook"
```

**Payload del Webhook:**
```json
{
  "event": "job.completed",
  "job_id": "uuid",
  "status": "completed",
  "timestamp": "2026-02-10T20:05:00Z",
  "data": {
    "notes_detected": 487,
    "processing_time": 45.2,
    "files": {
      "midi": "url-to-midi",
      "json": "url-to-json"
    }
  }
}
```

## 🧪 Testing

### Tests Unitarios

```bash
pytest tests/unit -v
```

### Tests de Integración

```bash
pytest tests/integration -v
```

### Coverage

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Load Testing

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

## 🛠️ Desarrollo

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

### Code Quality

```bash
# Format
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## 📊 Monitoreo

### Flower (Celery UI)

Accede a http://localhost:5555 para ver:
- Workers activos
- Tasks en progreso
- Estadísticas de procesamiento
- Historial de tasks

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Prometheus Metrics

```bash
curl http://localhost:8000/metrics
```

## 🐳 Docker

### Build

```bash
docker-compose -f docker-compose.prod.yml build
```

### Run

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📁 Estructura del Proyecto

```
music-2-notes/
├── src/
│   ├── api/              # FastAPI endpoints
│   │   ├── v1/           # API v1 routes
│   │   └── models/       # Pydantic models
│   ├── audio/            # Audio processing pipeline
│   │   ├── loader.py
│   │   ├── pitch_detector.py
│   │   ├── note_segmenter.py
│   │   └── midi_generator.py
│   ├── workers/          # Celery tasks
│   │   ├── celery_app.py
│   │   └── tasks/
│   ├── db/               # Database models & repos
│   │   ├── models/
│   │   └── repositories/
│   ├── core/             # Config, logging, security
│   └── storage/          # File storage abstraction
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── alembic/              # DB migrations
├── docker/               # Dockerfiles
├── docs/                 # Documentation
└── scripts/              # Utility scripts
```

## 🎵 Modelo CREPE

El proyecto usa [CREPE](https://github.com/marl/crepe) (Convolutional Representation for Pitch Estimation), un modelo de deep learning para pitch detection monofónico.

### Tamaños de Modelo

- **tiny**: Más rápido, menos preciso (~50ms/s audio)
- **small**: Balance para uso en tiempo real
- **medium**: ⭐ **RECOMENDADO** - Balance óptimo precisión/velocidad (~300ms/s audio)
- **large**: Mayor precisión, más lento
- **full**: Máxima precisión (~1s/s audio)

### Precisión

- Accuracy: ~95% para audio vocal limpio
- Resolución: 20 cents (1/5 de semitono)
- Rango: 6 octavas

## 🚦 Estado del Proyecto

- [x] FASE 0: Setup inicial
- [ ] FASE 1: Core de pitch detection
- [ ] FASE 2: Generación de MIDI y JSON
- [ ] FASE 3: API REST básica
- [ ] FASE 4: Sistema de jobs asíncrono
- [ ] FASE 5: Sistema de webhooks
- [ ] FASE 6: Testing y optimización
- [ ] FASE 7: Dockerización
- [ ] FASE 8: Documentación

## 📝 Licencia

MIT License

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una branch para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la branch (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📧 Contacto

- Project Link: https://github.com/your-org/music-2-notes
- Issues: https://github.com/your-org/music-2-notes/issues

## 🙏 Agradecimientos

- [CREPE](https://github.com/marl/crepe) - CNN-based pitch tracking
- [librosa](https://librosa.org/) - Audio analysis library
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Celery](https://docs.celeryq.dev/) - Distributed task queue

---

**Hecho con ❤️ para la comunidad musical y de desarrolladores**
