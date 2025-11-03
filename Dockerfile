FROM python:3.10

# Instala Java (requerido por language-tool-python)
RUN apt-get update && apt-get install -y default-jre

# Instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tu código
COPY . /app
WORKDIR /app

EXPOSE 5000

CMD ["gunicorn", "eli_backend:app", "--bind", "0.0.0.0:5000"]