# gestion/views/dashboard.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Incidencia
from .utils import logger, no_cache


@login_required
@no_cache
def dashboard_view(request):
    """
    Renderiza la vista del panel principal (dashboard).

    Esta vista se encarga de recopilar datos y estadísticas clave para
    mostrarlos en la página de inicio de la aplicación después de que el
    usuario ha iniciado sesión.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla 'gestion/dashboard.html' con
                      el contexto de las estadísticas. En caso de error,
                      redirige a la página de inicio de sesión.

    Context:
        'total_incidencias' (int): El número total de incidencias registradas
                                   en el sistema.
    """
    logger.info(
        f"El usuario '{request.user}' ha accedido al menu principal.")

    try:
        # --- Recopilación de Estadísticas ---
        total_incidencias = Incidencia.objects.count()
        logger.info(
            f"Se contaron {total_incidencias} incidencias totales para mostrar en el dashboard.")

        # El contexto que se pasará a la plantilla.
        context = {
            'total_incidencias': total_incidencias,
            # Puedes añadir más estadísticas aquí en el futuro.
            # 'total_aplicaciones': Aplicacion.objects.count(),
            # 'incidencias_abiertas': Incidencia.objects.filter(estado__nombre='Abierto').count(),
        }

        # --- Renderizado de la Vista ---
        return render(request, 'gestion/dashboard.html', context)

    except Exception as e:
        # --- Manejo de Errores ---
        # Si ocurre un error al consultar la base de datos.
        logger.error(
            f"Error crítico al cargar los datos del dashboard para el usuario '{request.user}'. Error: {e}",
            # Registra el traceback completo para facilitar la depuración.
            exc_info=True
        )
        messages.error(
            request, "Ocurrió un error inesperado al cargar el panel principal. Por favor, intente de nuevo.")
        # Redirigir a una página segura, como el login, es una buena práctica en caso de fallo.
        return redirect('gestion:login')
