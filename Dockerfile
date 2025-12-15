# Usamos una imagen base oficial de Python ligera
FROM python:3.9-slim

# Establecemos variables de entorno para optimizar Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalamos dependencias del sistema necesarias para mysqlclient y compilación
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copiamos e instalamos dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . /app/

# Script de entrada para esperar a la BD y correr migraciones
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Exponemos el puerto donde correrá Gunicorn
EXPOSE 8000

# Usamos el script de entrada
ENTRYPOINT ["/app/entrypoint.sh"]
