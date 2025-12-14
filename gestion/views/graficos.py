# gestion/views/graficos.py

from django.shortcuts import render
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db.models import Count, Q, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.contrib.auth.decorators import login_required
from .utils import no_cache, logger  # Se importa logger
from ..models import Incidencia, Aplicacion, Bloque, Estado, Severidad, CodigoCierre, Usuario, GrupoResolutor

# Constante para el nombre del grupo especial
GRUPO_ESPECIAL_INDRA_D = 'INDRA_D'


def get_filtered_incidencias(request):
    """
    Función auxiliar para filtrar incidencias basada en los parámetros GET.
    """
    queryset = Incidencia.objects.select_related(
        'aplicacion', 'estado', 'bloque', 'severidad', 'codigo_cierre', 'usuario_asignado', 'grupo_resolutor'
    ).all()

    # He añadido un log para ver los filtros que llegan al backend. ¡Esto es clave!
    logger.info(f"Filtros recibidos en el backend: {request.GET.dict()}")

    # --- Lógica de filtrado ---
    # Se comprueba que el valor del filtro exista y no sea una cadena vacía.
    if aplicativo_id := request.GET.get('aplicativo'):
        queryset = queryset.filter(aplicacion_id=aplicativo_id)

    if bloque_id := request.GET.get('bloque'):
        queryset = queryset.filter(bloque_id=bloque_id)

    if fecha_desde_str := request.GET.get('fecha_desde'):
        if fecha_desde := _parse_date(fecha_desde_str):
            queryset = queryset.filter(
                fecha_ultima_resolucion__gte=fecha_desde)

    if fecha_hasta_str := request.GET.get('fecha_hasta'):
        if fecha_hasta := _parse_date(fecha_hasta_str):
            fecha_hasta_fin_dia = fecha_hasta + timedelta(days=1)
            queryset = queryset.filter(
                fecha_ultima_resolucion__lt=fecha_hasta_fin_dia)

    if severidad_id := request.GET.get('severidad'):
        queryset = queryset.filter(severidad_id=severidad_id)

    if year := request.GET.get('year'):
        queryset = queryset.filter(fecha_ultima_resolucion__year=year)

    if month := request.GET.get('month'):
        queryset = queryset.filter(fecha_ultima_resolucion__month=month)

    if codigo_cierre_id := request.GET.get('codigo_cierre'):
        queryset = queryset.filter(codigo_cierre_id=codigo_cierre_id)

    if usuario_id := request.GET.get('usuario'):
        queryset = queryset.filter(usuario_asignado_id=usuario_id)

    if grupo_resolutor_id := request.GET.get('grupo_resolutor'):
        if grupo_resolutor_id.isdigit():
            queryset = queryset.filter(grupo_resolutor_id=grupo_resolutor_id)
        elif grupo_resolutor_id == 'exclude_indra_d':
            try:
                indra_d_grupo = GrupoResolutor.objects.get(
                    desc_grupo_resol__iexact='INDRA_D')
                queryset = queryset.exclude(
                    grupo_resolutor_id=indra_d_grupo.id)
            except GrupoResolutor.DoesNotExist:
                logger.warning(
                    "Se intentó filtrar excluyendo 'INDRA_D', pero el grupo no existe.")

    if cumple_sla := request.GET.get('cumple_sla'):
        if cumple_sla == 'No Calculado':
            queryset = queryset.filter(cumple_sla__startswith='No Calculado')
        else:
            queryset = queryset.filter(cumple_sla=cumple_sla)

    return queryset


def _parse_date(date_string):
    """Función auxiliar para parsear fechas de forma segura."""
    if not date_string:
        return None
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@login_required
@no_cache
def graficos_view(request):
    """
    Renderiza la página de gráficos y pasa los datos para los selectores de filtro.
    """
    # ... (Esta función no requiere cambios)
    aplicaciones = Aplicacion.objects.all().order_by('nombre_aplicacion')
    bloques = Bloque.objects.all().order_by('desc_bloque')
    severidades = Severidad.objects.all().order_by('desc_severidad')
    codigos_cierre = CodigoCierre.objects.all().order_by('cod_cierre')
    usuarios = Usuario.objects.all().order_by('nombre')
    grupos_resolutores = GrupoResolutor.objects.all().order_by('desc_grupo_resol')
    years = Incidencia.objects.filter(fecha_ultima_resolucion__isnull=False).dates(
        'fecha_ultima_resolucion', 'year', order='DESC')
    months = [
        {'value': 1, 'name': 'Enero'}, {'value': 2, 'name': 'Febrero'},
        {'value': 3, 'name': 'Marzo'}, {'value': 4, 'name': 'Abril'},
        {'value': 5, 'name': 'Mayo'}, {'value': 6, 'name': 'Junio'},
        {'value': 7, 'name': 'Julio'}, {'value': 8, 'name': 'Agosto'},
        {'value': 9, 'name': 'Septiembre'}, {'value': 10, 'name': 'Octubre'},
        {'value': 11, 'name': 'Noviembre'}, {'value': 12, 'name': 'Diciembre'},
    ]
    context = {
        'aplicaciones': aplicaciones, 'bloques': bloques, 'severidades': severidades,
        'codigos_cierre': codigos_cierre, 'usuarios': usuarios, 'years': years, 'months': months,
        'grupos_resolutores': grupos_resolutores,
    }
    return render(request, 'gestion/graficos.html', context)


@login_required
@no_cache
def graficos_data_json(request):
    """
    Devuelve los datos agregados para los gráficos en formato JSON.
    """
    total_general_incidencias = Incidencia.objects.count()
    incidencias_filtradas = get_filtered_incidencias(request)
    total_filtrado_incidencias = incidencias_filtradas.count()

    indra_d_grupo_id = None
    try:
        indra_d_grupo = GrupoResolutor.objects.get(
            desc_grupo_resol__iexact=GRUPO_ESPECIAL_INDRA_D)
        indra_d_grupo_id = indra_d_grupo.id
    except GrupoResolutor.DoesNotExist:
        logger.warning(
            f"El grupo resolutor '{GRUPO_ESPECIAL_INDRA_D}' no fue encontrado. No se aplicará la exclusión.")

    incidencias_sin_indra_d = incidencias_filtradas
    if indra_d_grupo_id:
        incidencias_sin_indra_d = incidencias_filtradas.exclude(
            grupo_resolutor_id=indra_d_grupo_id)

    # --- QUERIES CORREGIDAS CON Value() ---

    # Gráfico 1: Incidencias por Aplicativo
    data_aplicativo = (
        incidencias_sin_indra_d
        # <-- CORRECCIÓN
        .annotate(app_nombre=Coalesce('aplicacion__nombre_aplicacion', Value('No Asignado')))
        .values('app_nombre')
        .annotate(total=Count('id'))
        .order_by('-total')[:15]
    )

    # Gráfico 2: Incidencias por mes
    data_por_mes = (
        incidencias_sin_indra_d
        .filter(fecha_ultima_resolucion__isnull=False)
        .annotate(mes=TruncMonth('fecha_ultima_resolucion'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )

    # Gráfico 3: Incidencias por Severidad
    data_severidad = (
        incidencias_sin_indra_d
        # <-- CORRECCIÓN
        .annotate(sev_desc=Coalesce('severidad__desc_severidad', Value('Sin Severidad')))
        .values('sev_desc')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # Gráfico 4: Top 15 Códigos de Cierre
    data_codigos_cierre = (
        incidencias_sin_indra_d
        # <-- CORRECCIÓN
        .annotate(cod_cierre_val=Coalesce('codigo_cierre__cod_cierre', Value('No Asignado')))
        .values('cod_cierre_val')
        .annotate(total=Count('id'))
        .order_by('-total')[:15]
    )

    # Gráfico 5: Incidencias por INDRA_D vs Otros
    count_indra_d = 0
    if indra_d_grupo_id:
        count_indra_d = incidencias_filtradas.filter(
            grupo_resolutor_id=indra_d_grupo_id).count()
    count_otros = total_filtrado_incidencias - count_indra_d
    data_por_indra_d = {'labels': [
        GRUPO_ESPECIAL_INDRA_D, 'Otros Grupos'], 'values': [count_indra_d, count_otros]}

    # Preparación de los datos para la respuesta JSON
    meses_es = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
                7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    chart_data = {
        'total_general': total_general_incidencias, 'total_filtrado': total_filtrado_incidencias,
        'por_aplicativo': {'labels': [item['app_nombre'] for item in data_aplicativo], 'values': [item['total'] for item in data_aplicativo]},
        'por_mes': {'labels': [f"{meses_es.get(item['mes'].month, '')} {item['mes'].year}" for item in data_por_mes if item.get('mes')], 'values': [item['total'] for item in data_por_mes if item.get('mes')]},
        'por_severidad': {'labels': [item['sev_desc'] for item in data_severidad], 'values': [item['total'] for item in data_severidad]},
        'por_codigo_cierre': {'labels': [item['cod_cierre_val'] for item in data_codigos_cierre], 'values': [item['total'] for item in data_codigos_cierre]},
        'por_indra_d': data_por_indra_d
    }

    return JsonResponse(chart_data)


@login_required
def get_codigos_cierre_ajax(request):
    """
    Devuelve una lista de Códigos de Cierre en JSON.
    """
    # ... (Esta función no requiere cambios)
    aplicativo_id = request.GET.get('aplicativo_id')
    if aplicativo_id:
        codigos = CodigoCierre.objects.filter(
            aplicacion_id=aplicativo_id).order_by('cod_cierre')
    else:
        codigos = CodigoCierre.objects.all().order_by('cod_cierre')
    data = [{'id': c.id, 'text': c.cod_cierre} for c in codigos]
    return JsonResponse({'codigos': data})
