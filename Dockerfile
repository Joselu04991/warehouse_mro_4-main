# Imagen base
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Copiar dependencias
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el proyecto
COPY . .

# Railway asigna automáticamente una variable PORT
ENV PYTHONUNBUFFERED=1

# Exponer puerto
EXPOSE 8000

# Comando final – NUNCA usar "$PORT" literal, Railway lo reemplaza
CMD ["bash", "-c", "gunicorn --bind 0.0.0.0:${PORT} wsgi:app"]
