#!/usr/bin/env fish
# Script para verificar que el setup inicial está completo (Fish shell)

echo "🔍 Verificando setup de Music-2-Notes..."
echo ""

# Colors
set GREEN \e\[0\;32m
set RED \e\[0\;31m
set YELLOW \e\[1\;33m
set NC \e\[0m

set SUCCESS "$GREEN✓$NC"
set FAIL "$RED✗$NC"
set WARN "$YELLOW⚠$NC"

# Check Python version
echo -n "Python 3.10+: "
if command -v python3 > /dev/null 2>&1
    set PYTHON_VERSION (python3 --version | cut -d' ' -f2)
    set MAJOR (echo $PYTHON_VERSION | cut -d'.' -f1)
    set MINOR (echo $PYTHON_VERSION | cut -d'.' -f2)
    if test $MAJOR -eq 3; and test $MINOR -ge 10
        echo -e "$SUCCESS $PYTHON_VERSION"
    else
        echo -e "$FAIL $PYTHON_VERSION (Se requiere 3.10+)"
    end
else
    echo -e "$FAIL No encontrado"
end

# Check Docker
echo -n "Docker: "
if command -v docker > /dev/null 2>&1
    set DOCKER_VERSION (docker --version | cut -d' ' -f3 | tr -d ',')
    if docker ps > /dev/null 2>&1
        echo -e "$SUCCESS $DOCKER_VERSION (running)"
    else
        echo -e "$WARN $DOCKER_VERSION (not running)"
    end
else
    echo -e "$FAIL No encontrado"
end

# Check Docker Compose
echo -n "Docker Compose: "
if command -v docker-compose > /dev/null 2>&1
    set COMPOSE_VERSION (docker-compose --version | cut -d' ' -f4 | tr -d ',')
    echo -e "$SUCCESS $COMPOSE_VERSION"
else
    echo -e "$FAIL No encontrado"
end

echo ""
echo "📁 Verificando estructura del proyecto..."

# Check directories
set DIRS \
    src/api \
    src/audio \
    src/workers \
    src/db \
    src/core \
    src/storage \
    tests/unit \
    tests/integration \
    tests/fixtures \
    alembic \
    docker \
    docs \
    scripts

for dir in $DIRS
    if test -d $dir
        echo -e "  $SUCCESS $dir"
    else
        echo -e "  $FAIL $dir"
    end
end

echo ""
echo "📄 Verificando archivos de configuración..."

# Check files
set FILES \
    pyproject.toml \
    docker-compose.yml \
    .env \
    .env.example \
    .gitignore \
    .pre-commit-config.yaml \
    README.md

for file in $FILES
    if test -f $file
        echo -e "  $SUCCESS $file"
    else
        echo -e "  $FAIL $file"
    end
end

echo ""
echo "🐳 Verificando servicios Docker..."

# Check if Docker is running
if docker ps > /dev/null 2>&1
    # Check PostgreSQL
    echo -n "  PostgreSQL: "
    if docker ps | grep -q music2notes-postgres
        echo -e "$SUCCESS Running"
    else
        echo -e "$WARN No ejecutándose (ejecutar: docker-compose up -d postgres)"
    end

    # Check Redis
    echo -n "  Redis: "
    if docker ps | grep -q music2notes-redis
        echo -e "$SUCCESS Running"
    else
        echo -e "$WARN No ejecutándose (ejecutar: docker-compose up -d redis)"
    end
else
    echo -e "  $WARN Docker daemon no está corriendo"
end

echo ""
echo "✨ Próximos pasos (Fish shell):"
echo ""
echo "1. Crear virtual environment:"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate.fish  # ← Nota el .fish"
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
