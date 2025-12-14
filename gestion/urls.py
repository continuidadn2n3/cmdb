# gestion/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views  # Importa el paquete de vistas completo
from gestion.views import recommendations

app_name = 'gestion'

urlpatterns = [
    # Le decimos a LoginView que use tu plantilla 'home.html'
    path('', auth_views.LoginView.as_view(
        template_name='gestion/home.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='gestion:login'), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logs/', views.view_logs, name='view_logs'),
    path('logs/download/', views.download_log_file, name='download_log'),
    path('aplicaciones/', views.aplicaciones_view, name='aplicaciones'),

    path('aplicaciones/registrar/', views.registrar_aplicacion_view,
         name='registrar_aplicacion'),
    path('aplicaciones/eliminar/<int:pk>/',
         views.eliminar_aplicacion_view, name='eliminar_aplicacion'),
    path('aplicaciones/editar/<int:pk>/',
         views.editar_aplicacion_view, name='editar_aplicacion'),
    path('aplicaciones/cargar/', views.carga_masiva_view,
         name='carga_masiva_aplicaciones'),
    path('aplicaciones/exportar-csv/', views.exportar_aplicaciones_csv,
         name='exportar_aplicaciones_csv'),

    path('codigos-cierre/', views.codigos_cierre_view, name='codigos_cierre'),
    path('codigos-cierre/registrar/', views.registrar_cod_cierre_view,
         name='registrar_cod_cierre'),
    path('codigos-cierre/eliminar/<int:pk>/',
         views.eliminar_cod_cierre_view, name='eliminar_cod_cierre'),
    path('codigos-cierre/editar/<int:pk>/',
         views.editar_cod_cierre_view, name='editar_cod_cierre'),
    path('codigos-cierre/cargar/', views.carga_masiva_cod_cierre_view,
         name='carga_masiva_cod_cierre'),
    path('codigos-cierre/exportar-csv/', views.exportar_codigos_cierre_csv,
         name='exportar_codigos_cierre_csv'),
    path('ajax/get-ultimos-codigos-cierre/<int:aplicacion_id>/',
         views.obtener_ultimos_codigos_cierre, name='get_ultimos_codigos_cierre'),

    path('incidencias/', views.incidencias_view, name='incidencias'),
    path('incidencias/registrar/', views.registrar_incidencia_view,
         name='registrar_incidencia'),
    path('ajax/get-codigos-cierre/<int:aplicacion_id>/',
         views.get_codigos_cierre_por_aplicacion, name='get_codigos_cierre_por_aplicacion'),
    path('incidencias/editar/<int:pk>/',
         views.editar_incidencia_view, name='editar_incidencia'),
    path('incidencias/eliminar/<int:pk>/',
         views.eliminar_incidencia_view, name='eliminar_incidencia'),
    path('incidencias/carga-masiva/', views.carga_masiva_incidencia_view,
         name='carga_masiva_incidencia'),
    path('incidencias/carga-masiva-inicial/',
         views.carga_masiva_inicial_view, name='carga_masiva_inicial'),

    path('incidencias/calcular-sla/',
         views.calculo_sla.calcular_sla_view, name='calcular_sla'),
    path('incidencias/exportar-sla-csv/',
         views.exportar_sla_csv_view, name='exportar_sla_csv'),
    path('incidencias/exportar-reporte/', views.exportar_incidencias_reporte_view,
         name='exportar_incidencias_reporte'),

    # Nuevas rutas para la página de gráficos y su endpoint de datos
    path('graficos/', views.graficos_view, name='graficos'),
    path('graficos/data/', views.graficos_data_json, name='graficos_data'),
    path('graficos/codigos-cierre-por-aplicativo/',
         views.get_codigos_cierre_ajax, name='codigos_cierre_por_aplicativo'),

    path('mantenedores/', views.mantenedores_main,
         name='mantenedores_main'),

    # === NUEVAS RUTAS PARA LOS MANTENEDORES ===
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/registrar/', views.registrar_usuario,
         name='registrar_usuario'),
    path('usuarios/editar/<int:pk>/',
         views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:pk>/',
         views.eliminar_usuario, name='eliminar_usuario'),

    path('estados/', views.listar_estados, name='listar_estados'),
    path('estados/registrar/', views.registrar_estado,
         name='registrar_estado'),
    path('estados/editar/<int:pk>/',
         views.editar_estado, name='editar_estado'),
    path('estados/eliminar/<int:pk>/',
         views.eliminar_estado, name='eliminar_estado'),

    path('grupos-resolutores/',
         views.listar_grupos, name='listar_grupos'),
    path('grupos-resolutores/registrar/',
         views.registrar_grupo, name='registrar_grupo'),
    path('grupos-resolutores/editar/<int:pk>/',
         views.editar_grupo, name='editar_grupo'),
    path('grupos-resolutores/eliminar/<int:pk>/',
         views.eliminar_grupo, name='eliminar_grupo'),

    path('reglas-sla/', views.listar_reglas_sla,
         name='listar_reglas_sla'),
    path('reglas-sla/registrar/', views.registrar_regla_sla,
         name='registrar_regla_sla'),
    path('reglas-sla/editar/<int:pk>/',
         views.editar_regla_sla, name='editar_regla_sla'),
    path('reglas-sla/eliminar/<int:pk>/',
         views.eliminar_regla_sla, name='eliminar_regla_sla'),

    path('dias-feriados/', views.listar_dias_feriados,
         name='listar_dias_feriados'),
    path('dias-feriados/registrar/',
         views.registrar_dia_feriado, name='registrar_dia_feriado'),
    path('dias-feriados/editar/<int:pk>/',
         views.editar_dia_feriado, name='editar_dia_feriado'),
    path('dias-feriados/eliminar/<int:pk>/',
         views.eliminar_dia_feriado, name='eliminar_dia_feriado'),

    path('horarios-laborales/', views.listar_horarios_laborales,
         name='listar_horarios_laborales'),
    path('horarios-laborales/registrar/',
         views.registrar_horario_laboral, name='registrar_horario_laboral'),
    path('horarios-laborales/editar/<int:pk>/',
         views.editar_horario_laboral, name='editar_horario_laboral'),
    path('horarios-laborales/eliminar/<int:pk>/',
         views.eliminar_horario_laboral, name='eliminar_horario_laboral'),

    # La ruta de la API 'recommend-closure-code/' se ha movido a 'api_urls.py'.
    # Nos aseguramos de que solo la página de prueba esté aquí.

    # Página de prueba para la recomendación
    path('recommendation-test/', recommendations.recommendation_test_page,
         name='recommendation_test_page'),
]
