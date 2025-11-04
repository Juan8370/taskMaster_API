# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (optional minimal)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install deps
COPY requeriments.txt ./
RUN python -m pip install --upgrade pip && pip install -r requeriments.txt

# Copy app
COPY app ./app

# Expose
EXPOSE 8000

# Default envs (proporciona valores reales en la plataforma de despliegue; si no se define DATABASE_URL,
# la app usa SQLite por defecto via app/config.py)
ENV SECRET_KEY="change-me" \
    ACCESS_TOKEN_EXPIRE_MINUTES=60

# Start
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
