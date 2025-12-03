FROM python:3.10-slim

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

WORKDIR /app

# Copiar requirements primero para cache eficiente
COPY requirements.txt .

# Instalar dependencias Python optimizadas
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# Copiar aplicación (nombre específico: eli_backend.py)
COPY eli_backend.py .

# Variables de entorno para optimizar
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=5000
ENV PYTHONIOENCODING=utf-8
ENV FLASK_DEBUG=0

# Usar usuario no-root para seguridad
RUN useradd -m -u 1000 eliuser \
    && chown -R eliuser:eliuser /app
USER eliuser

EXPOSE 5000

# Comando específico para eli_backend.py con optimizaciones para plan gratuito
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "90", "--preload", "eli_backend:app"]