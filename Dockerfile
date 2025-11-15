# Dockerfile para Consultia - Incluye poppler para PDFs
FROM python:3.11-slim

# Instalar poppler-utils para pdf2image
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements del backend
COPY consultia/backend/requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del backend
COPY consultia/backend/ ./backend/

# Copiar frontend compilado
COPY consultia/frontend/dist/consultia ./frontend/dist/consultia

# Exponer puerto
EXPOSE 8001

# Comando para iniciar el servidor
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8001"]
