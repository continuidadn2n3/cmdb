# Proyecto Evo CMDB

Descripción breve del proyecto. Esta aplicación gestiona una Base de Datos de Configuración (CMDB) para el seguimiento de aplicaciones, incidencias y sus componentes asociados.

---

## Requisitos del Entorno

Para ejecutar este proyecto, necesitarás tener instalado el siguiente software en tu sistema:

- **Python**: `3.12.6`
- **MySQL**: `8.0.x`

---

## Guía de Instalación Local

Sigue estos pasos para configurar el entorno de desarrollo en tu máquina.

### 1. Clona el Repositorio
```bash
git clone <URL_DEL_REPOSITORIO>
cd evo_cmdb
```

### 2. Crea y Activa un Entorno Virtual
Esto aislará las dependencias del proyecto para evitar conflictos.
```bash
# Crear el entorno (se creará una carpeta llamada "venv")
python -m venv venv

# Activar en Windows (PowerShell/CMD)
.\venv\Scripts\activate

# Activar en macOS/Linux
source venv/bin/activate
```

### 3. Instala las Dependencias
```bash
pip install -r requirements_dev.txt
```

### 4. Configura las Variables de Entorno
Copia el archivo de ejemplo `.env.example` a un nuevo archivo llamado `.env` y edítalo con tus credenciales locales.
```bash
# En Windows: copy .env.example .env
# En macOS/Linux: cp .env.example .env
```
**¡Importante!** Abre el archivo `.env` y rellena las variables `SECRET_KEY`, `DB_NAME`, `DB_USER`, etc.

### 5. Prepara la Base de Datos
Ejecuta las migraciones para crear las tablas y luego carga los datos iniciales necesarios para que la aplicación funcione.
```bash
python manage.py migrate
python manage.py cargar_datos_iniciales
```

### 6. Crea un Superusuario
Necesitarás un usuario administrador para acceder al panel de Django (`/admin`).
```bash
python manage.py createsuperuser
```

### 7. ¡Ejecuta el Proyecto!
```bash
python manage.py runserver
```
La aplicación estará disponible en `http://127.0.0.1:8000`.