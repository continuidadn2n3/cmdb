# gestion/views/utils.py

import logging
from functools import wraps

# El logger se puede configurar aquí o en cada archivo
logger = logging.getLogger(__name__)


def no_cache(view_func):
    """Decorador que añade cabeceras a la respuesta para evitar caché."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    return _wrapped_view


def is_staff(user):
    """Verifica si un usuario pertenece al staff."""
    return user.is_staff
