FROM python:3.10-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Instalar curl para health checks
RUN apt-get update && apt-get install -y curl

WORKDIR /app

# Copiar requirements primero
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Instalar googletrans fix
RUN pip install --no-cache-dir httpx==0.24.1

# Copiar aplicación
COPY . .

# Crear usuario no-root
RUN useradd -m -u 1000 eliuser && chown -R eliuser:eliuser /app
USER eliuser

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/api/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]