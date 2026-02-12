# Music-2-Notes AI Skill

Skill para que agentes de IA procesen audio vocal, detecten notas musicales y generen archivos MIDI usando la API de Music-2-Notes.

## Skill Prompt

Copia el siguiente bloque como instruccion de sistema o skill en tu agente de IA:

```markdown
# Skill: music2notes - Analisis de audio vocal y generacion MIDI

Eres un asistente que puede procesar archivos de audio vocal para detectar
notas musicales y generar archivos MIDI usando la API de Music-2-Notes.

## API Base URL
{MUSIC2NOTES_API_URL}

## Endpoints disponibles

### Crear job de analisis
POST /api/v1/jobs
Content-Type: multipart/form-data

Parametros (form-data):
- audio_file (required): Archivo de audio (WAV, MP3, FLAC, OGG, M4A). Max 100MB.
- model_size (optional): "tiny" (rapido) o "full" (preciso). Default: "tiny"
- confidence_threshold (optional): 0.0-1.0. Default: 0.95
- webhook_url (optional): URL para notificacion al completar

Response (202):
{
  "job_id": "uuid",
  "status": "pending",
  "created_at": "ISO datetime"
}

### Consultar estado
GET /api/v1/jobs/{job_id}

Response:
{
  "job_id": "uuid",
  "status": "pending|processing|completed|failed",
  "progress": 0-100,
  "audio_filename": "string",
  "audio_duration": float,
  "model_size": "tiny|full",
  "notes_detected": int,
  "processing_time": float,
  "error_message": "string o null"
}

### Obtener resultado completo
GET /api/v1/jobs/{job_id}/result

Response:
{
  "job_id": "uuid",
  "status": "completed",
  "result": {
    "metadata": {
      "audio_duration": float,
      "model_size": "string",
      "confidence_threshold": float,
      "notes_detected": int
    },
    "notes": [
      {
        "midi_number": int,
        "note_name": "C4",
        "start_time": float,
        "duration": float,
        "end_time": float,
        "frequency": float,
        "confidence": float,
        "velocity": int
      }
    ]
  }
}

### Descargar MIDI
GET /api/v1/jobs/{job_id}/download/midi
Response: archivo .mid (audio/midi)

### Descargar JSON
GET /api/v1/jobs/{job_id}/download/json
Response: archivo .json (application/json)

### Health check
GET /api/v1/health
Response: {"status": "healthy", "database": "up", "storage": "up"}

## Flujo de uso

1. Enviar audio via POST /api/v1/jobs
2. Hacer polling a GET /api/v1/jobs/{job_id} cada 2-5 segundos
3. Cuando status == "completed", obtener resultado o descargar archivos
4. Si status == "failed", revisar error_message

## Notas importantes

- El procesamiento es asincrono. El POST retorna inmediatamente con un job_id.
- Modelo "tiny": rapido (~5s para 1min de audio con GPU). Bueno para previews.
- Modelo "full": preciso (~60s para 1min de audio con GPU). Para produccion.
- confidence_threshold 0.95 filtra solo notas donde CREPE tiene 95%+ certeza.
- Un valor mas bajo (ej: 0.7) detecta mas notas pero incluye mas falsos positivos.
- El audio debe contener solo voz (sin instrumentos). Para mejores resultados, usar audio limpio.

## Ejemplo con curl

```bash
# Crear job
curl -X POST "{MUSIC2NOTES_API_URL}/api/v1/jobs" \
  -F "audio_file=@vocal.wav" \
  -F "model_size=tiny"

# Consultar estado
curl "{MUSIC2NOTES_API_URL}/api/v1/jobs/{job_id}"

# Descargar MIDI
curl "{MUSIC2NOTES_API_URL}/api/v1/jobs/{job_id}/download/midi" -o resultado.mid

# Descargar JSON
curl "{MUSIC2NOTES_API_URL}/api/v1/jobs/{job_id}/download/json" -o resultado.json
```

## Ejemplo con Python

```python
import httpx
import time

API = "{MUSIC2NOTES_API_URL}"

# Enviar audio
with open("vocal.wav", "rb") as f:
    r = httpx.post(f"{API}/api/v1/jobs", files={"audio_file": f})
job_id = r.json()["job_id"]

# Esperar resultado
while True:
    status = httpx.get(f"{API}/api/v1/jobs/{job_id}").json()
    if status["status"] in ("completed", "failed"):
        break
    time.sleep(3)

# Obtener notas
if status["status"] == "completed":
    result = httpx.get(f"{API}/api/v1/jobs/{job_id}/result").json()
    for note in result["result"]["notes"]:
        print(f"{note['note_name']} @ {note['start_time']}s ({note['duration']}s)")
```
```

## Instalacion en diferentes IAs

### Claude Code (Anthropic)

Guarda la skill en tu proyecto:

```bash
mkdir -p .claude/skills
# Copia el contenido del bloque "Skill Prompt" de arriba en:
# .claude/skills/music2notes.md
```

Reemplaza `{MUSIC2NOTES_API_URL}` por tu URL real (ej: la URL de ngrok de Colab).

Luego usala con:
```
/skill music2notes
```

### ChatGPT (Custom GPT / Instructions)

1. Ve a "Configure" en tu GPT
2. En "Instructions", pega el contenido del bloque "Skill Prompt"
3. Reemplaza `{MUSIC2NOTES_API_URL}` por tu URL real
4. En "Actions", crea una accion con el OpenAPI schema (ver abajo)

### Cursor / Windsurf / Copilot

Crea un archivo `.cursorrules` o `.windsurfrules` en la raiz de tu proyecto:

```bash
# Pega el contenido del bloque "Skill Prompt" en:
# .cursorrules (Cursor)
# .windsurfrules (Windsurf)
# .github/copilot-instructions.md (Copilot)
```

### Cualquier agente con soporte de herramientas (function calling)

Define estas tools/functions:

```json
[
  {
    "name": "create_audio_analysis_job",
    "description": "Enviar un archivo de audio para analisis de notas musicales",
    "parameters": {
      "type": "object",
      "properties": {
        "audio_file_path": {"type": "string", "description": "Ruta al archivo de audio"},
        "model_size": {"type": "string", "enum": ["tiny", "full"], "default": "tiny"},
        "confidence_threshold": {"type": "number", "default": 0.95}
      },
      "required": ["audio_file_path"]
    }
  },
  {
    "name": "get_job_status",
    "description": "Consultar estado de un job de analisis de audio",
    "parameters": {
      "type": "object",
      "properties": {
        "job_id": {"type": "string"}
      },
      "required": ["job_id"]
    }
  },
  {
    "name": "get_job_result",
    "description": "Obtener resultado con notas musicales detectadas",
    "parameters": {
      "type": "object",
      "properties": {
        "job_id": {"type": "string"}
      },
      "required": ["job_id"]
    }
  },
  {
    "name": "download_midi",
    "description": "Descargar archivo MIDI generado",
    "parameters": {
      "type": "object",
      "properties": {
        "job_id": {"type": "string"}
      },
      "required": ["job_id"]
    }
  }
]
```

## OpenAPI Schema (para ChatGPT Actions)

```yaml
openapi: 3.0.0
info:
  title: Music-2-Notes API
  version: 0.1.0
  description: Vocal audio analysis and MIDI generation
servers:
  - url: "{MUSIC2NOTES_API_URL}"
paths:
  /api/v1/jobs:
    post:
      operationId: createJob
      summary: Create audio analysis job
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              required: [audio_file]
              properties:
                audio_file:
                  type: string
                  format: binary
                model_size:
                  type: string
                  enum: [tiny, full]
                  default: tiny
                confidence_threshold:
                  type: number
                  default: 0.95
      responses:
        "202":
          description: Job created
  /api/v1/jobs/{job_id}:
    get:
      operationId: getJobStatus
      summary: Get job status
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Job status
  /api/v1/jobs/{job_id}/result:
    get:
      operationId: getJobResult
      summary: Get analysis result with detected notes
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Analysis result
  /api/v1/jobs/{job_id}/download/midi:
    get:
      operationId: downloadMidi
      summary: Download MIDI file
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: MIDI file
  /api/v1/jobs/{job_id}/download/json:
    get:
      operationId: downloadJson
      summary: Download JSON with notes
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: JSON file
  /api/v1/health:
    get:
      operationId: healthCheck
      summary: Health check
      responses:
        "200":
          description: Service health
```
