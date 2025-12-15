#!/bin/bash

# Verificar si la base de datos está lista (espera activa)
echo "Esperando a la base de datos..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "Base de datos iniciada."

# Ejecutar migraciones
echo "Aplicando migraciones..."
python manage.py migrate

# Recolectar estáticos
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# Iniciar servidor Gunicorn
echo "Iniciando Gunicorn..."
exec gunicorn cmdb_project.wsgi:application --bind 0.0.0.0:8000
