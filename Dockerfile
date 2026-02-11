FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema para librosa/soundfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsndfile1 && \
    rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copiar código
COPY src/ src/

# Crear carpetas necesarias
RUN mkdir -p data storage

# Exponer puerto
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health')" || exit 1

# Ejecutar
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
