# gestion/views/calculo_sla.py

import csv
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, time, timedelta

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .utils import logger
from ..models import Incidencia, ReglaSLA, HorarioLaboral, DiaFeriado, Usuario

# --- Funciones de Utilidad ---


def normalizar_texto(texto):
    """
    Limpia y estandariza una cadena de texto.

    Realiza las siguientes operaciones:
    1. Convierte a minúsculas.
    2. Elimina acentos y diacríticos (ej. 'camión' -> 'camion').
    3. Reemplaza múltiples espacios en blanco por uno solo.
    4. Elimina espacios al inicio y al final.
    5. Devuelve una cadena vacía si la entrada no es un string.

    Args:
        texto (str): La cadena de texto a normalizar.

    Returns:
        str: El texto normalizado.
    """
    if not isinstance(texto, str):
        return ""
    texto = re.sub(r'\s+', ' ', texto).strip().lower()
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def parsear_bitacora(bitacora_texto, incidencia_id="N/A"):
    """
    Convierte el texto plano de una bitácora en una lista estructurada de entradas.

    Utiliza una expresión regular para encontrar todas las entradas que sigan el
    patrón "dd-mm-yyyy hh:mm:ss, usuario, mensaje".

    Args:
        bitacora_texto (str): El contenido completo de la bitácora.
        incidencia_id (str, opcional): El ID de la incidencia, para logging de errores.

    Returns:
        list: Una lista de diccionarios, cada uno representando una entrada de la
              bitácora, ordenada por fecha. Ejemplo de una entrada:
              {'fecha_hora': datetime_obj, 'usuario': 'nombre.usuario', 'mensaje': 'texto...'}
    """
    if not bitacora_texto:
        return []

    logger.info(
        f"Iniciando parseo de bitácora para Incidencia ID {incidencia_id}.")
    bitacora_texto_limpia = bitacora_texto.replace('¶', '\n')
    entries = []
    # Expresión regular modificada para ser más flexible con los formatos de fecha/hora,
    # incluyendo formatos con año de 2/4 dígitos y AM/PM.
    regex = re.compile(
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\s+\d{1,2}:\d{2}:\d{2}(?:\s*[ap]\.m\.)?)\s*,\s*([^,]+?)\s*,\s*(.*?)(?=\s*[\r\n]+\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\Z)', re.DOTALL)

    matches = regex.finditer(bitacora_texto_limpia)
    for match in matches:
        date_str, user_raw, message = match.groups()
        dt_obj_naive = None

        # Preparamos el string para que sea compatible con strptime.
        # Se pasa a minúsculas y se quitan los puntos de a.m./p.m.
        parseable_str = date_str.strip().lower().replace(
            'a.m.', 'am').replace('p.m.', 'pm')

        # Lista de formatos a intentar. El orden es importante.
        date_formats_to_try = [
            "%d/%m/%Y %H:%M:%S",    # Formato común: 08/05/2025 16:40:04
            "%d-%m-%Y %H:%M:%S",    # Formato con guiones: 25-04-2025 18:02:32
            # Nuevo formato AM/PM: 26/8/25 1:52:49 p.m.
            "%d/%m/%y %I:%M:%S %p",
        ]

        for fmt in date_formats_to_try:
            try:
                dt_obj_naive = datetime.strptime(parseable_str, fmt)
                # Si se parsea correctamente, salimos del bucle
                break
            except ValueError:
                # Si el formato no coincide, probamos el siguiente
                continue

        if dt_obj_naive:
            dt_obj_aware = timezone.make_aware(dt_obj_naive)
            entries.append({"fecha_hora": dt_obj_aware, "usuario": normalizar_texto(
                user_raw), "mensaje": message.strip()})
        else:
            # Si después de intentar todos los formatos no se pudo parsear, se registra un warning.
            logger.warning(
                f"Error parseando fecha en bitácora para Incidencia ID {incidencia_id}: '{date_str}'. No se pudo procesar con los formatos conocidos. Ignorando entrada.")

    entries.sort(key=lambda x: x["fecha_hora"])
    logger.info(
        f"Parseo de bitácora para Incidencia ID {incidencia_id} finalizado. Se encontraron {len(entries)} entradas válidas.")
    return entries


def is_working_time(dt_obj, horario_laboral, dias_feriados):
    """
    Verifica si una fecha/hora específica cae dentro del horario laboral.

    Args:
        dt_obj (datetime): El objeto de fecha y hora a verificar.
        horario_laboral (dict): Diccionario con el horario laboral por día de la semana.
        dias_feriados (set): Un conjunto de fechas de días feriados.

    Returns:
        bool: True si la fecha/hora está dentro del horario laboral, False en caso contrario.
    """
    # Un punto en el tiempo no es laboral si es un día feriado.
    if dt_obj.date() in dias_feriados:
        return False

    dia_semana = dt_obj.weekday()  # Lunes es 0, Domingo es 6
    horario_dia = horario_laboral.get(dia_semana)

    # No es laboral si no hay horario definido para ese día o si está marcado como cerrado (None).
    if not horario_dia or not horario_dia[0]:
        return False

    # Es laboral si la hora actual está entre la hora de inicio y fin para ese día.
    hora_inicio, hora_fin = horario_dia
    return hora_inicio <= dt_obj.time() <= hora_fin


def calcular_tiempo_efectivo(start_dt, end_dt, horario_laboral, dias_feriados, es_critica_24_7=False):
    """
    Calcula el tiempo laboral efectivo transcurrido entre dos fechas.

    Si la incidencia es crítica (24/7), calcula la diferencia total de tiempo.
    De lo contrario, itera segundo a segundo, contando solo aquellos que caen
    dentro del horario laboral definido.

    Args:
        start_dt (datetime): Fecha y hora de inicio del intervalo.
        end_dt (datetime): Fecha y hora de fin del intervalo.
        horario_laboral (dict): Diccionario de horarios laborales.
        dias_feriados (set): Conjunto de fechas de días feriados.
        es_critica_24_7 (bool): Si es True, ignora horarios y feriados.

    Returns:
        timedelta: El tiempo laboral efectivo transcurrido.
    """
    if start_dt >= end_dt:
        return timedelta(0)

    # Modo 24/7: el cálculo es directo y rápido.
    if es_critica_24_7:
        logger.debug(f"Cálculo 24/7 para intervalo de {start_dt} a {end_dt}.")
        return end_dt - start_dt

    # Modo Horario Laboral: cálculo segundo a segundo.
    tiempo_laboral_total = timedelta(0)
    puntero_tiempo = start_dt

    while puntero_tiempo < end_dt:
        if is_working_time(puntero_tiempo, horario_laboral, dias_feriados):
            tiempo_laboral_total += timedelta(seconds=1)
        puntero_tiempo += timedelta(seconds=1)

    return tiempo_laboral_total


def _timedelta_to_hms(td):
    """Convierte un objeto timedelta a un string con formato HH:MM:SS."""
    if not td:
        return "00:00:00"
    total_seconds = int(td.total_seconds())
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# --- Lógica Principal y Vistas ---

def calcular_sla_desde_bitacora(incidencia, gestores_norm, horarios, feriados, reglas_sla):
    """
    Orquesta el cálculo completo del SLA para una única incidencia, generando un log detallado.
    """
    logger.info(
        f"\n--- Iniciando análisis de SLA para Incidencia: {incidencia.incidencia} (ID: {incidencia.id}) ---")

    # --- 1. VALIDACIONES PREVIAS (LÓGICA MODIFICADA) ---

    # --- CAMBIO: Se define la lista de IDs de grupos que SÍ se incluyen en el cálculo.
    GRUPOS_SLA_INCLUIDOS = {7, 11, 12, 13, 14, 15}

    # Se omite el cálculo si el bloque es 5 O si el grupo resolutor NO está en la lista de incluidos.
    if (incidencia.bloque_id == 5 or
            incidencia.grupo_resolutor_id not in GRUPOS_SLA_INCLUIDOS):

        # Lógica mejorada para un mensaje de log más claro
        motivo = ""
        if incidencia.bloque_id == 5:
            motivo = "el bloque es 'Sin Bloque'"
        elif incidencia.grupo_resolutor:
            motivo = f"el grupo resolutor '{incidencia.grupo_resolutor.desc_grupo_resol}' no está incluido en el cálculo"
        else:
            # Este caso cubre incidencias sin grupo resolutor asignado.
            motivo = "la incidencia no tiene un grupo resolutor válido para el cálculo"

        logger.info(f"-> CÁLCULO OMITIDO porque {motivo}.")
        return {"cumple_sla": "No Aplica"}

    # El resto de las validaciones (por falta de datos) no cambia.
    campos_faltantes = [campo for campo, valor in [("Severidad", incidencia.severidad), ("Aplicación", incidencia.aplicacion), (
        "Criticidad de la Aplicación", incidencia.aplicacion.criticidad if incidencia.aplicacion else None)] if not valor]
    if campos_faltantes:
        logger.warning(
            f"-> CÁLCULO OMITIDO. Faltan datos: {', '.join(campos_faltantes)}.")
        return {"cumple_sla": "No Calculado (Faltan Datos)"}

    # 2. Inicio del análisis y procesamiento de bitácora
    bitacora_entries = parsear_bitacora(incidencia.bitacora, incidencia.id)
    es_critica_24_7 = (normalizar_texto(
        incidencia.severidad.desc_severidad) == "critica")
    tiempo_gestion_total = timedelta(0)

    # 3. Bucle de análisis de segmentos con logging detallado
    if len(bitacora_entries) > 1:
        for i in range(len(bitacora_entries) - 1):
            entrada_actual = bitacora_entries[i]
            entrada_siguiente = bitacora_entries[i+1]

            start_dt, end_dt = entrada_actual["fecha_hora"], entrada_siguiente["fecha_hora"]
            start_user, end_user = entrada_actual['usuario'], entrada_siguiente['usuario']

            # Logs de información del segmento
            logger.info(
                f"Desde {start_dt.strftime('%d-%m-%Y %H:%M:%S')} hasta {end_dt.strftime('%d-%m-%Y %H:%M:%S')}.")
            logger.info(f"-> De: '{start_user}' | A: '{end_user}'")

            # Lógica de decisión
            es_respuesta_de_gestor = end_user in gestores_norm
            reloj_no_pausado = 'pendiente' not in normalizar_texto(
                entrada_actual['mensaje'])

            # Log de análisis basado en la decisión
            if es_respuesta_de_gestor and reloj_no_pausado:
                tiempo_segmento = calcular_tiempo_efectivo(
                    start_dt, end_dt, horarios, feriados, es_critica_24_7)
                tiempo_gestion_total += tiempo_segmento
                logger.info(
                    f" ANÁLISIS: Se cuenta el tiempo. Gestor '{end_user}' respondió. Tiempo sumado: {_timedelta_to_hms(tiempo_segmento)}")
            elif not es_respuesta_de_gestor:
                logger.info(
                    f" ANÁLISIS: No se cuenta. El usuario '{end_user}' no es un gestor.")
            else:  # not reloj_no_pausado
                logger.info(
                    f" ANÁLISIS: No se cuenta. El reloj está pausado por nota 'Pendiente' de '{start_user}'.")

            logger.info("-" * 60)

    # Fallback si el tiempo de gestión es 0 en incidencias no críticas.
    if tiempo_gestion_total == timedelta(0) and not es_critica_24_7 and bitacora_entries:
        tiempo_gestion_total = timedelta(minutes=20)
        logger.info(
            "-> Aplicando fallback de 20 minutos por tiempo de gestión 0.")

    # 4. Log del resultado final
    logger.info(
        f"-> TIEMPO TOTAL DE GESTIÓN PARA {incidencia.incidencia}: {_timedelta_to_hms(tiempo_gestion_total)}\n")

    # 5. Comparación con SLA y devolución de resultados
    clave_regla = (incidencia.severidad.id,
                   incidencia.aplicacion.criticidad.id)
    tiempo_sla_objetivo = reglas_sla.get(clave_regla)
    cumple_sla = "SLA No Definido"
    if tiempo_sla_objetivo:
        cumple_sla = "Sí" if tiempo_gestion_total <= tiempo_sla_objetivo else "No"
    elif not bitacora_entries:
        cumple_sla = "No Calculado (Bitácora Vacía)"

    ultimo_gestor = next((entry["usuario"] for entry in reversed(
        bitacora_entries) if entry["usuario"] in gestores_norm), "N/A")

    return {
        "incidencia": incidencia,
        "tiempo_gestion_calculado": tiempo_gestion_total,
        "tiempo_gestion_horas": _timedelta_to_hms(tiempo_gestion_total),
        "sla_objetivo": tiempo_sla_objetivo,
        "sla_objetivo_horas": _timedelta_to_hms(tiempo_sla_objetivo),
        "cumple_sla": cumple_sla,
        "ultimo_gestor": ultimo_gestor
    }


@require_POST
def calcular_sla_view(request):
    """
    Endpoint de API para calcular y guardar el SLA de múltiples incidencias.

    Recibe una petición POST con un cuerpo JSON que contiene una lista de IDs de
    incidencias. Procesa cada una, actualiza su estado de SLA en la base de
    datos y devuelve un resumen de los resultados.

    Args:
        request (HttpRequest): La solicitud HTTP (debe ser POST).

    Returns:
        JsonResponse: Un objeto JSON con el estado de la operación y los resultados.
    """
    logger.info(
        f"Recibida petición para calcular SLA por el usuario '{request.user}'.")
    try:
        data = json.loads(request.body)
        incidencia_ids = data.get('incidencia_ids', [])
        if not incidencia_ids:
            logger.warning(
                "La petición de cálculo de SLA no contenía IDs de incidencias.")
            return JsonResponse({'status': 'error', 'message': 'No se seleccionaron incidencias.'}, status=400)

        logger.info(f"Se procesarán {len(incidencia_ids)} incidencias.")

        # --- Precarga de datos para eficiencia ---
        incidencias_a_procesar = Incidencia.objects.filter(
            id__in=incidencia_ids).select_related('aplicacion__criticidad', 'severidad')
        gestores_norm = {normalizar_texto(u.usuario)
                         for u in Usuario.objects.all()}
        horarios = {h.dia_semana: (h.hora_inicio, h.hora_fin)
                    for h in HorarioLaboral.objects.all()}
        feriados = {d.fecha for d in DiaFeriado.objects.all()}
        reglas_sla = {(r.severidad_id, r.criticidad_aplicacion_id): r.tiempo_sla for r in ReglaSLA.objects.all()}

        stats = Counter()
        resultados_vista = []
        for inc in incidencias_a_procesar:
            resultado = calcular_sla_desde_bitacora(
                inc, gestores_norm, horarios, feriados, reglas_sla)
            stats[resultado.get("cumple_sla", "Error")] += 1

            # Actualización en la base de datos
            inc.tiempo_sla_calculado = resultado.get(
                "tiempo_gestion_calculado")
            inc.cumple_sla = resultado.get("cumple_sla", "Error")
            inc.save(update_fields=['tiempo_sla_calculado', 'cumple_sla'])
            resultados_vista.append({'id': inc.id, 'incidencia': inc.incidencia,
                                    'cumple_sla': inc.cumple_sla, 'tiempo_sla': resultado.get("tiempo_gestion_horas")})

        # --- Log del resumen final ---
        logger.info(
            "\n--- RESUMEN DE ESTADÍSTICAS DE SLA (Cálculo desde Tabla) ---")
        for estado, count in stats.items():
            logger.info(f"{estado:<40} : {count}")
        logger.info(
            f"{'Total de incidencias procesadas':<40} : {len(incidencias_a_procesar)}")
        logger.info(
            "----------------------------------------------------------\n")

        return JsonResponse({'status': 'success', 'message': f'Se procesaron {len(resultados_vista)} incidencias.', 'results': resultados_vista})
    except Exception as e:
        logger.error(
            f"Error en la vista calcular_sla_view: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Ocurrió un error inesperado.'}, status=500)


def exportar_sla_csv_view(request):
    """
    Genera y exporta un reporte de SLA en formato CSV.

    Esta vista calcula el SLA para un conjunto de incidencias (respetando los
    filtros de la URL) y devuelve el resultado como un archivo CSV descargable.

    Args:
        request (HttpRequest): La solicitud HTTP (puede tener parámetros GET para filtrar).

    Returns:
        HttpResponse: Un archivo CSV para ser descargado por el navegador.
    """
    # 1. Obtención de Filtros y Log de Inicio
    filtros_aplicados = [f"{k}='{v}'" for k, v in request.GET.items() if v]
    log_filtros = f"con filtros: {', '.join(filtros_aplicados)}" if filtros_aplicados else "sin filtros"
    logger.info(
        f"Usuario '{request.user}' ha solicitado exportación CSV de SLA {log_filtros}.")

    # 2. Precarga de Datos y Aplicación de Filtros
    gestores_norm = {normalizar_texto(u.usuario)
                     for u in Usuario.objects.all()}
    horarios = {h.dia_semana: (h.hora_inicio, h.hora_fin)
                for h in HorarioLaboral.objects.all()}
    feriados = {d.fecha for d in DiaFeriado.objects.all()}
    reglas_sla = {(r.severidad_id, r.criticidad_aplicacion_id): r.tiempo_sla for r in ReglaSLA.objects.all()}

    incidencias_qs = Incidencia.objects.select_related(
        'aplicacion__criticidad', 'severidad', 'usuario_asignado').all()

    # Aplicar filtros de la URL
    if filtro_incidencia := request.GET.get('incidencia'):
        incidencias_qs = incidencias_qs.filter(
            incidencia__icontains=filtro_incidencia)
    if filtro_fecha_desde := request.GET.get('fecha_desde'):
        try:
            fecha_aware = timezone.make_aware(
                datetime.strptime(filtro_fecha_desde, '%Y-%m-%d'))
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__gte=fecha_aware)
        except (ValueError, TypeError):
            pass
    if filtro_fecha_hasta := request.GET.get('fecha_hasta'):
        try:
            fecha_aware = timezone.make_aware(datetime.strptime(
                filtro_fecha_hasta, '%Y-%m-%d') + timedelta(days=1))
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__lt=fecha_aware)
        except (ValueError, TypeError):
            pass

    # 3. Generación del CSV
    response = HttpResponse(content_type='text/csv', headers={
                            'Content-Disposition': 'attachment; filename="reporte_sla_bitacora.csv"'})
    # BOM para compatibilidad con Excel
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response)
    writer.writerow(['Incidencia', 'Fecha Resolucion', 'Ultimo Gestor', 'Aplicativo', 'Criticidad Aplicativo',
                    'Severidad', 'SLA Objetivo (Horas)', 'Tiempo Gestion (Horas)', 'Cumple SLA'])

    stats = Counter()
    total_procesadas = 0
    for inc in incidencias_qs:
        total_procesadas += 1
        resultado = calcular_sla_desde_bitacora(
            inc, gestores_norm, horarios, feriados, reglas_sla)
        stats[resultado.get("cumple_sla", "Error")] += 1

        if "Error" not in resultado.get("cumple_sla", ""):
            writer.writerow([
                inc.incidencia,
                inc.fecha_ultima_resolucion.strftime(
                    '%Y-%m-%d %H:%M:%S') if inc.fecha_ultima_resolucion else "N/A",
                resultado.get("ultimo_gestor", "N/A"),
                inc.aplicacion.nombre_aplicacion if inc.aplicacion else "N/A",
                inc.aplicacion.criticidad.desc_criticidad if inc.aplicacion and inc.aplicacion.criticidad else "N/A",
                inc.severidad.desc_severidad if inc.severidad else "N/A",
                resultado.get("sla_objetivo_horas", "N/A"),
                resultado.get("tiempo_gestion_horas", "N/A"),
                resultado.get("cumple_sla", "Error")
            ])

    # 4. Log del Resumen Final
    logger.info("\n--- RESUMEN DE ESTADÍSTICAS DE SLA (Exportación CSV) ---")
    for estado, count in stats.items():
        logger.info(f"{estado:<40} : {count}")
    logger.info(
        f"{'Total de incidencias procesadas':<40} : {total_procesadas}")
    logger.info("------------------------------------------------------\n")
    logger.info(f"Exportación CSV para '{request.user}' completada.")

    response.set_cookie('descargaFinalizada', 'true', max_age=20, path='/')
    return response
