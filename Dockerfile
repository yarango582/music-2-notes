FROM python:3.12-slim AS builder

WORKDIR /build

# Dependencias del sistema para compilar paquetes nativos
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Instalar PyTorch + torchaudio CPU-only (evita CUDA ~6GB)
RUN pip install --no-cache-dir \
    torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Instalar resto de dependencias (torch ya esta, no se reinstala)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# --- Stage final (imagen limpia) ---
FROM python:3.12-slim

WORKDIR /app

# Solo dependencias runtime (ffmpeg para audio, libsndfile para soundfile)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

# Copiar paquetes Python instalados desde builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar codigo fuente
COPY src/ src/

# Crear carpetas necesarias
RUN mkdir -p data storage

ENV PORT=8000
EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/v1/health')" || exit 1

CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}
