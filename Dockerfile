# --- Imagen base ---
FROM python:3.11-slim

# --- Variables de Entorno ---
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# --- Argumentos de Build ---
ARG VCS_REF
LABEL org.opencontainers.image.revision=$VCS_REF \
      org.opencontainers.image.source="https://github.com/TechCrafted-dev/Backend"

# --- Directorio de Trabajo ---
WORKDIR /app

# --- Instalación de Dependencias ---
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Copia del Código de la Aplicación ---
COPY main.py .
COPY modules/ ./modules/

# --- Creación del Directorio de Datos ---
RUN mkdir -p /app/data

# --- Exposición del Puerto ---
EXPOSE 3000

# --- Comando de Ejecución ---
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
