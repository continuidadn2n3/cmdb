# gestion/views/logs.py

import os
from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from .utils import no_cache, is_staff, logger


@login_required
@user_passes_test(is_staff)
@no_cache
def view_logs(request):
    """
    Renderiza una página que muestra las últimas 800 líneas del archivo de log.

    Esta vista está restringida solo para personal (staff). Busca el archivo
    'logs.log' en el directorio base del proyecto, lee su contenido y lo
    pasa a la plantilla para su visualización. Maneja de forma segura los
    casos en que el archivo no existe o no se puede leer.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla 'gestion/view_logs.html' con el
                      contenido del log.

    Context:
        'log_content' (str): Las últimas 800 líneas del log o un mensaje de
                             error si el archivo no pudo ser leído.
    """
    # --- 1. Registro de Acceso ---
    logger.info(
        f"El usuario staff '{request.user}' ha accedido al visor de logs.")

    # --- 2. Definición y Verificación de la Ruta del Archivo ---
    log_file_path = settings.BASE_DIR / 'logs.log'
    log_content = ""

    if os.path.exists(log_file_path):
        # --- 3. Lectura del Archivo de Log ---
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                # Se leen todas las líneas y se seleccionan solo las últimas 800
                lines = f.readlines()[-800:]
                log_content = ''.join(lines)
                logger.info(
                    f"Se han cargado con éxito las últimas {len(lines)} líneas del log.")
        except Exception as e:
            # Manejo de errores si el archivo existe pero no se puede leer
            logger.error(
                f"Error al leer el archivo de log '{log_file_path}': {e}", exc_info=True)
            log_content = f"Hubo un error al intentar leer el archivo de log: {e}"
    else:
        # Manejo del caso en que el archivo de log no existe
        logger.warning(
            f"El archivo de log no fue encontrado en la ruta: {log_file_path}")
        log_content = "El archivo de log 'logs.log' no ha sido encontrado en el directorio base del proyecto."

    # --- 4. Renderizado de la Plantilla ---
    context = {'log_content': log_content}
    return render(request, 'gestion/view_logs.html', context)


@login_required
@user_passes_test(is_staff)
@no_cache
def download_log_file(request):
    """
    Permite a un usuario del personal (staff) descargar el archivo de log completo.

    Esta vista busca el archivo 'logs.log' y, si lo encuentra, lo transmite
    como una descarga de archivo adjunto usando `FileResponse` para un manejo
    eficiente de la memoria. Si el archivo no existe, lanza un error 404.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        FileResponse: Una respuesta que inicia la descarga del archivo de log.

    Raises:
        Http404: Si el archivo 'logs.log' no se encuentra en el directorio base.
    """
    # --- 1. Definición de la Ruta y Registro de la Solicitud ---
    log_file_path = settings.BASE_DIR / 'logs.log'
    logger.info(
        f"El usuario '{request.user}' ha solicitado la descarga del log completo.")

    # --- 2. Verificación y Envío del Archivo ---
    if os.path.exists(log_file_path):
        # FileResponse es la forma ideal de enviar archivos en Django,
        # ya que los transmite en lugar de cargarlos completamente en memoria.
        return FileResponse(open(log_file_path, 'rb'), as_attachment=True, filename='logs.log')
    else:
        # Si el archivo no existe, se registra el error y se lanza un 404.
        logger.error(
            f"Intento de descarga de un archivo de log inexistente en: {log_file_path}")
        raise Http404("El archivo de log no fue encontrado.")
