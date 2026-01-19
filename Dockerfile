FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["gunicorn", "wsgi:app", "-b", "0.0.0.0:8080", "--workers", "3"]
