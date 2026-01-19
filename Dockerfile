FROM python:3.11-slim

# Instalar dependencias del sistema (Tesseract, poppler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Instalar pip deps
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

ENV PORT=8080
EXPOSE 8080

CMD ["gunicorn", "wsgi:app", "-b", "0.0.0.0:8080", "--workers", "3"]
