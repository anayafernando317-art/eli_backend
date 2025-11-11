FROM python:3.10-slim

# Instala ffmpeg para pydub
RUN apt-get update && apt-get install -y ffmpeg

# Instala dependencias Python
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copia tu código
COPY . /app
WORKDIR /app

EXPOSE 5000

CMD ["gunicorn", "eli_backend:app", "--bind", "0.0.0.0:5000"]