# gestion/views/__init__.py

from .dashboard import dashboard_view
from .graficos import graficos_view, graficos_data_json, get_codigos_cierre_ajax
from .incidencias import incidencias_view, registrar_incidencia_view, editar_incidencia_view, eliminar_incidencia_view, get_codigos_cierre_por_aplicacion, carga_masiva_incidencia_view, exportar_incidencias_reporte_view, carga_masiva_inicial_view
from .aplicaciones import (aplicaciones_view, registrar_aplicacion_view,
                           eliminar_aplicacion_view, editar_aplicacion_view, carga_masiva_view, exportar_aplicaciones_csv, )
from .cod_cierre import (
    codigos_cierre_view, registrar_cod_cierre_view, eliminar_cod_cierre_view, editar_cod_cierre_view, carga_masiva_cod_cierre_view, obtener_ultimos_codigos_cierre, exportar_codigos_cierre_csv, )
from .logs import view_logs, download_log_file
from .calculo_sla import calcular_sla_view, exportar_sla_csv_view
# Importa todas las vistas de los mantenedores para que estén disponibles en el paquete 'views'
from .mantenedores_views import *
