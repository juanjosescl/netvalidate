#!/bin/bash
# Detiene el servicio netvalidate.
pkill -f "uvicorn netvalidate" && echo "✓ Servicio detenido" || echo "El servicio no estaba corriendo"
