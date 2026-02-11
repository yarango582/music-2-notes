# Despliegue de Music-2-Notes

## Opciones de Despliegue por Costo

### 1. Railway (Recomendado - $0/mes para empezar)

Railway ofrece $5 de crédito gratis por mes, suficiente para un servicio ligero.

**Pasos:**

```bash
# 1. Instalar Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Crear proyecto
railway init

# 4. Desplegar
railway up

# 5. Obtener URL
railway domain
```

**Variables de entorno en Railway:**
```
DATABASE_URL=sqlite+aiosqlite:///data/music2notes.db
STORAGE_PATH=/app/storage
DEFAULT_MODEL_SIZE=tiny
SECRET_KEY=<genera-un-secreto>
WEBHOOK_SECRET_KEY=<genera-otro-secreto>
```

**Limitaciones tier gratuito:**
- 512 MB RAM (suficiente para modelo tiny)
- 1 GB disco
- Duerme después de inactividad

---

### 2. Render (Gratis)

Render tiene un tier gratuito con 750 horas/mes.

**Pasos:**

1. Crear cuenta en https://render.com
2. Crear "New Web Service"
3. Conectar repositorio de GitHub
4. Configurar:
   - **Runtime**: Docker
   - **Plan**: Free
   - **Health Check Path**: `/api/v1/health`

**render.yaml** (crear en la raíz del proyecto):
```yaml
services:
  - type: web
    name: music-2-notes
    runtime: docker
    plan: free
    healthCheckPath: /api/v1/health
    envVars:
      - key: DATABASE_URL
        value: sqlite+aiosqlite:///data/music2notes.db
      - key: STORAGE_PATH
        value: /app/storage
      - key: DEFAULT_MODEL_SIZE
        value: tiny
      - key: SECRET_KEY
        generateValue: true
      - key: WEBHOOK_SECRET_KEY
        generateValue: true
```

**Limitaciones tier gratuito:**
- 512 MB RAM
- Spin down después de 15 min inactividad
- Sin disco persistente (datos se pierden en redeploy)

---

### 3. Fly.io (Gratis)

Fly.io ofrece hasta 3 VMs gratuitas con 256 MB RAM cada una.

**Pasos:**

```bash
# 1. Instalar flyctl
curl -L https://fly.io/install.sh | sh

# 2. Login
fly auth signup  # o fly auth login

# 3. Crear app
fly launch

# 4. Crear volumen persistente (para SQLite y archivos)
fly volumes create music2notes_data --size 1

# 5. Desplegar
fly deploy
```

**fly.toml** (crear en la raíz del proyecto):
```toml
app = "music-2-notes"
primary_region = "mia"  # Miami, o la región más cercana

[build]
  dockerfile = "Dockerfile"

[env]
  DATABASE_URL = "sqlite+aiosqlite:///data/music2notes.db"
  STORAGE_PATH = "/data/storage"
  DEFAULT_MODEL_SIZE = "tiny"

[mounts]
  source = "music2notes_data"
  destination = "/data"

[http_service]
  internal_port = 8000
  force_https = true

  [http_service.concurrency]
    type = "connections"
    hard_limit = 25
    soft_limit = 20

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
```

**Ventajas:**
- Volumen persistente (datos sobreviven redeploy)
- Auto-scaling
- HTTPS automático
- Mejor para producción

---

### 4. VPS Barato ($2-5/mes)

Para más control, un VPS económico:

| Proveedor    | RAM    | Precio/mes | Notas                    |
|-------------|--------|-----------|--------------------------|
| Hetzner     | 2 GB   | $3.79     | Excelente rendimiento    |
| DigitalOcean| 1 GB   | $4.00     | Droplet básico           |
| Vultr       | 1 GB   | $2.50     | El más barato            |
| Oracle Cloud| 4 GB   | $0.00     | Always Free tier         |

**Oracle Cloud Always Free** es la mejor opción para costo $0 real:
- 1 OCPU + 4 GB RAM (ARM)
- 200 GB disco
- Sin límite de tiempo

**Pasos con VPS:**

```bash
# 1. Conectar al VPS
ssh root@tu-vps-ip

# 2. Instalar Docker
curl -fsSL https://get.docker.com | sh

# 3. Clonar repositorio
git clone https://github.com/tu-org/music-2-notes.git
cd music-2-notes

# 4. Crear .env
cp .env.example .env
nano .env  # Editar variables

# 5. Build y ejecutar
docker build -t music2notes .
docker run -d \
  --name music2notes \
  -p 8000:8000 \
  -v music2notes_data:/app/data \
  -v music2notes_storage:/app/storage \
  --env-file .env \
  --restart unless-stopped \
  music2notes

# 6. (Opcional) Nginx como reverse proxy con SSL
apt install nginx certbot python3-certbot-nginx
```

---

## Despliegue Local (Desarrollo)

```bash
# 1. Activar entorno virtual
source .venv/bin/activate.fish  # Fish shell

# 2. Ejecutar API
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 3. Acceder a:
#    - API: http://localhost:8000
#    - Docs: http://localhost:8000/docs
#    - Health: http://localhost:8000/api/v1/health
```

---

## Resumen de Opciones

| Plataforma       | Costo     | RAM      | Persistencia | Ideal para         |
|-----------------|-----------|----------|-------------|-------------------|
| Railway         | $0-5/mes  | 512 MB   | Limitada    | Prototipo rápido  |
| Render          | $0/mes    | 512 MB   | No          | Demo              |
| Fly.io          | $0/mes    | 512 MB   | Si (vol.)   | Producción ligera |
| Oracle Cloud    | $0/mes    | 4 GB     | Si          | Producción real   |
| Hetzner VPS     | $3.79/mes | 2 GB     | Si          | Producción seria  |

---

## Notas Importantes

### RAM y Modelo CREPE
- **Modelo `tiny`**: ~200 MB RAM (funciona en tier gratuito)
- **Modelo `full`**: ~1.5 GB RAM (necesita VPS con 2+ GB)

### Persistencia de Datos
- SQLite y archivos generados necesitan disco persistente
- En Render (gratis) los datos se pierden en cada redeploy
- Fly.io con volumen es la mejor opción gratuita con persistencia

### HTTPS
- Railway, Render y Fly.io dan HTTPS gratis automáticamente
- En VPS propio, usa Certbot + Nginx

### Consideraciones de Seguridad
- Cambiar `SECRET_KEY` y `WEBHOOK_SECRET_KEY` en producción
- No exponer el puerto de la base de datos
- Configurar CORS correctamente para tu dominio
