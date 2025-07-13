#!/bin/sh

CONFIG_FILE=/app/data/config.py

if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ Error: config.py no encontrado en /app/data"
  echo "Crea uno basado en config_template.py"
  exit 1
fi

# Enlace simbólico para que el import funcione como `from config import ...`
ln -sf /app/data/config.py /app/config.py

exec "$@"
