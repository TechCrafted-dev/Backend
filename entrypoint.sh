#!/bin/sh

if [ ! -f /app/config.py ]; then
  echo "❌ Error: config.py no encontrado. Debes montar un archivo de configuración basado en config_template.py."
  echo "Usa el volumen: ./config.py:/app/config.py"
  exit 1
fi

exec "$@"
