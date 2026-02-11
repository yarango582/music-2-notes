#!/bin/bash
# Script para verificar que el setup inicial está completo

echo "🔍 Verificando setup de Music-2-Notes..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SUCCESS="${GREEN}✓${NC}"
FAIL="${RED}✗${NC}"
WARN="${YELLOW}⚠${NC}"

# Check Python version
echo -n "Python 3.10+: "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    if [ $MAJOR -eq 3 ] && [ $MINOR -ge 10 ]; then
        echo -e "$SUCCESS $PYTHON_VERSION"
    else
        echo -e "$FAIL $PYTHON_VERSION (Se requiere 3.10+)"
    fi
else
    echo -e "$FAIL No encontrado"
fi

# Check Docker
echo -n "Docker: "
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    if docker ps &> /dev/null; then
        echo -e "$SUCCESS $DOCKER_VERSION (running)"
    else
        echo -e "$WARN $DOCKER_VERSION (not running)"
    fi
else
    echo -e "$FAIL No encontrado"
fi

# Check Docker Compose
echo -n "Docker Compose: "
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f4 | tr -d ',')
    echo -e "$SUCCESS $COMPOSE_VERSION"
else
    echo -e "$FAIL No encontrado"
fi

echo ""
echo "📁 Verificando estructura del proyecto..."

# Check directories
DIRS=(
    "src/api"
    "src/audio"
    "src/workers"
    "src/db"
    "src/core"
    "src/storage"
    "tests/unit"
    "tests/integration"
    "tests/fixtures"
    "alembic"
    "docker"
    "docs"
    "scripts"
)

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "  $SUCCESS $dir"
    else
        echo -e "  $FAIL $dir"
    fi
done

echo ""
echo "📄 Verificando archivos de configuración..."

# Check files
FILES=(
    "pyproject.toml"
    "docker-compose.yml"
    ".env"
    ".env.example"
    ".gitignore"
    ".pre-commit-config.yaml"
    "README.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  $SUCCESS $file"
    else
        echo -e "  $FAIL $file"
    fi
done

echo ""
echo "🐳 Verificando servicios Docker..."

# Check if Docker is running
if docker ps &> /dev/null; then
    # Check PostgreSQL
    echo -n "  PostgreSQL: "
    if docker ps | grep -q music2notes-postgres; then
        echo -e "$SUCCESS Running"
    else
        echo -e "$WARN No ejecutándose (ejecutar: docker-compose up -d postgres)"
    fi

    # Check Redis
    echo -n "  Redis: "
    if docker ps | grep -q music2notes-redis; then
        echo -e "$SUCCESS Running"
    else
        echo -e "$WARN No ejecutándose (ejecutar: docker-compose up -d redis)"
    fi
else
    echo -e "  $WARN Docker daemon no está corriendo"
fi

echo ""
echo "✨ Próximos pasos:"
echo ""
echo "1. Crear virtual environment:"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo ""
echo "2. Instalar dependencias:"
echo "   pip install -e \".[dev]\""
echo ""
echo "3. Levantar servicios:"
echo "   docker-compose up -d postgres redis"
echo ""
echo "4. Inicializar base de datos:"
echo "   alembic upgrade head"
echo ""
echo "5. Ejecutar tests:"
echo "   pytest tests/"
echo ""
