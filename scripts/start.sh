#!/bin/bash
# Inicia el servicio netvalidate en background.
# Uso: ./scripts/start.sh

set -e

cd "$(dirname "$0")/.."

# Apagar instancia previa si existe
pkill -f "uvicorn netvalidate" 2>/dev/null || true
sleep 1

# Cargar variables de .env
set -a
source .env
set +a

# Verificar variables esenciales
if [ -z "$NETVALIDATE_API_KEY" ]; then
    echo "ERROR: NETVALIDATE_API_KEY no está en .env"
    exit 1
fi

# Activar venv
source .venv/bin/activate

# Lanzar
nohup uvicorn netvalidate.main:app --host 0.0.0.0 --port 8000 \
    > /tmp/uvicorn.log 2>&1 &

sleep 3

# Verificar
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✓ Servicio corriendo en http://localhost:8000"
    echo "  Swagger UI: http://localhost:8000/docs"
    echo "  Logs:       tail -f /tmp/uvicorn.log"
    echo "  Parar:      ./scripts/stop.sh"
else
    echo "✗ El servicio no respondió. Ver logs:"
    tail -20 /tmp/uvicorn.log
    exit 1
fi
