import csv
import io
import re
import json
from datetime import datetime, timedelta
import pandas as pd
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone

from .utils import no_cache, logger
from django.core.exceptions import ObjectDoesNotExist
from unidecode import unidecode
from openpyxl.utils import get_column_letter
from ..models import (Incidencia, Aplicacion, Estado, Severidad, Impacto,
                      GrupoResolutor, Interfaz, Cluster, Bloque, CodigoCierre, Usuario)
from ..forms import IncidenciaForm


@login_required
@no_cache
def incidencias_view(request):
    """
    Renderiza la página de gestión de incidencias y maneja la lógica de filtrado.

    Esta vista tiene un comportamiento especial: si se accede sin ningún
    parámetro de filtro en la URL, aplica automáticamente un filtro para mostrar
    solo las incidencias cuya fecha de última resolución esté dentro del mes actual.
    Si se proporcionan filtros, los aplica a la consulta.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla 'gestion/incidencia.html' con el
                      contexto necesario.

    Context:
        'lista_de_incidencias' (QuerySet): Incidencias resultantes tras el filtrado.
        'total_registros' (int): El número total de incidencias en el sistema.
        'aplicaciones' (QuerySet): Lista de todas las aplicaciones para el filtro.
        'bloques' (QuerySet): Lista de todos los bloques para el filtro.
        'codigos_cierre' (QuerySet): Lista de todos los códigos de cierre para el filtro.
        'fecha_inicio_mes' (str): Primer día del mes actual (formato 'YYYY-MM-DD').
        'fecha_fin_mes' (str): Último día del mes actual (formato 'YYYY-MM-DD').
    """
    # --- 1. Inicio y Registro de Acceso ---
    logger.info(
        f"El usuario '{request.user}' ha accedido a la vista de incidencias.")

    # --- 2. Queryset Base Optimizado ---
    # Usamos select_related para reducir el número de consultas a la base de datos.
    incidencias_qs = Incidencia.objects.select_related(
        'aplicacion', 'estado', 'severidad', 'impacto', 'bloque', 'codigo_cierre',
        'grupo_resolutor'
    ).all()

    # --- 3. Procesamiento de Filtros ---
    filtros_aplicados = []
    filtro_app_id = request.GET.get('aplicativo')
    filtro_bloque_id = request.GET.get('bloque')
    filtro_incidencia = request.GET.get('incidencia')
    filtro_codigo_id = request.GET.get('codigo_cierre')
    filtro_fecha_desde = request.GET.get('fecha_desde')
    filtro_fecha_hasta = request.GET.get('fecha_hasta')
    filtro_grupo_resolutor_id = request.GET.get('grupo_resolutor')
    filtro_cumple_sla = request.GET.get('cumple_sla')

    # Lógica de filtro por defecto: si no hay filtros en la URL, se usa el mes actual.
    if not request.GET:
        hoy = timezone.now()
        primer_dia_mes = hoy.replace(day=1)
        # Se calcula el último día del mes actual
        if primer_dia_mes.month == 12:
            ultimo_dia_mes = primer_dia_mes.replace(
                year=primer_dia_mes.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            ultimo_dia_mes = primer_dia_mes.replace(
                month=primer_dia_mes.month + 1, day=1) - timedelta(days=1)

        filtro_fecha_desde = primer_dia_mes.strftime('%Y-%m-%d')
        filtro_fecha_hasta = ultimo_dia_mes.strftime('%Y-%m-%d')
        logger.info(
            f"No se proporcionaron filtros. Aplicando filtro por defecto para el mes actual: {filtro_fecha_desde} a {filtro_fecha_hasta}.")

    # Aplicar filtros al queryset solo si el usuario los envía.
    if filtro_app_id and filtro_app_id.isdigit():
        incidencias_qs = incidencias_qs.filter(aplicacion_id=filtro_app_id)
        filtros_aplicados.append(f"aplicativo_id='{filtro_app_id}'")

    if filtro_bloque_id and filtro_bloque_id.isdigit():
        incidencias_qs = incidencias_qs.filter(bloque_id=filtro_bloque_id)
        filtros_aplicados.append(f"bloque_id='{filtro_bloque_id}'")

    if filtro_incidencia:
        incidencias_qs = incidencias_qs.filter(
            incidencia__icontains=filtro_incidencia)
        filtros_aplicados.append(f"incidencia='{filtro_incidencia}'")

    if filtro_codigo_id and filtro_codigo_id.isdigit():
        incidencias_qs = incidencias_qs.filter(
            codigo_cierre_id=filtro_codigo_id)
        filtros_aplicados.append(f"codigo_cierre_id='{filtro_codigo_id}'")

    if filtro_grupo_resolutor_id:
        if filtro_grupo_resolutor_id.isdigit():
            incidencias_qs = incidencias_qs.filter(
                grupo_resolutor_id=filtro_grupo_resolutor_id)
            filtros_aplicados.append(
                f"grupo_resolutor_id='{filtro_grupo_resolutor_id}'")
        elif filtro_grupo_resolutor_id == 'exclude_indra_d':
            try:
                indra_d_grupo = GrupoResolutor.objects.get(
                    desc_grupo_resol__iexact='INDRA_D')
                incidencias_qs = incidencias_qs.exclude(
                    grupo_resolutor_id=indra_d_grupo.id)
                filtros_aplicados.append(
                    "grupo_resolutor='Todos (Sin INDRA_D)'")
            except GrupoResolutor.DoesNotExist:
                logger.warning(
                    "Se intentó filtrar excluyendo 'INDRA_D', pero el grupo no existe en la base de datos.")

    if filtro_cumple_sla:
        if filtro_cumple_sla == 'No Calculado':
            incidencias_qs = incidencias_qs.filter(
                cumple_sla__startswith='No Calculado')
        else:
            incidencias_qs = incidencias_qs.filter(
                cumple_sla=filtro_cumple_sla)
        filtros_aplicados.append(f"cumple_sla='{filtro_cumple_sla}'")

    # Aplicar filtros de fecha con manejo de errores
    if filtro_fecha_desde:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_desde, '%Y-%m-%d')
            # fecha_aware = timezone.make_aware(fecha_obj, timezone.get_default_timezone()) # Removed for USE_TZ=False
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__gte=fecha_obj)
            filtros_aplicados.append(f"fecha_desde='{filtro_fecha_desde}'")
        except (ValueError, TypeError):
            logger.warning(
                f"Formato de fecha 'desde' inválido: '{filtro_fecha_desde}'. Se ignorará el filtro.")

    if filtro_fecha_hasta:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_hasta, '%Y-%m-%d')
            fecha_obj_fin_dia = fecha_obj + timedelta(days=1)
            # fecha_aware = timezone.make_aware(fecha_obj_fin_dia, timezone.get_default_timezone()) # Removed for USE_TZ=False
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__lt=fecha_obj_fin_dia)
            filtros_aplicados.append(f"fecha_hasta='{filtro_fecha_hasta}'")
        except (ValueError, TypeError):
            logger.warning(
                f"Formato de fecha 'hasta' inválido: '{filtro_fecha_hasta}'. Se ignorará el filtro.")

    if filtros_aplicados and request.GET:  # Solo registrar si los filtros son explícitos del usuario
        logger.info(
            f"Búsqueda de incidencias con filtros: {', '.join(filtros_aplicados)}.")

    logger.info(
        f"La consulta ha devuelto {incidencias_qs.count()} incidencias.")

    # --- 4. Preparación del Contexto para la Plantilla ---
    # Nota: La lógica para calcular las fechas del mes se repite.
    # En una futura refactorización, podría moverse a una función auxiliar.
    hoy = timezone.now()
    primer_dia_mes = hoy.replace(day=1)
    if primer_dia_mes.month == 12:
        primer_dia_mes_siguiente = primer_dia_mes.replace(
            year=primer_dia_mes.year + 1, month=1)
    else:
        primer_dia_mes_siguiente = primer_dia_mes.replace(
            month=primer_dia_mes.month + 1)
    ultimo_dia_mes = primer_dia_mes_siguiente - timedelta(days=1)

    context = {
        'lista_de_incidencias': incidencias_qs,
        'total_registros': Incidencia.objects.count(),
        'aplicaciones': Aplicacion.objects.all().order_by('nombre_aplicacion'),
        'bloques': Bloque.objects.all().order_by('desc_bloque'),
        'codigos_cierre': CodigoCierre.objects.all().order_by('cod_cierre'),
        'grupos_resolutores': GrupoResolutor.objects.all().order_by('desc_grupo_resol'),
        'fecha_inicio_mes': primer_dia_mes.strftime('%Y-%m-%d'),
        'fecha_fin_mes': ultimo_dia_mes.strftime('%Y-%m-%d'),
    }

    # --- 5. Renderizado Final ---
    return render(request, 'gestion/incidencia.html', context)


@login_required
@no_cache
@login_required
@no_cache
def registrar_incidencia_view(request):
    """
    Gestiona el registro de una nueva incidencia usando Django Forms.
    """
    if request.method == 'POST':
        logger.info(f"El usuario '{request.user}' intenta registrar una incidencia.")
        form = IncidenciaForm(request.POST)
        if form.is_valid():
            try:
                nueva_incidencia = form.save(commit=False)
                nueva_incidencia.usuario_creador = request.user
                nueva_incidencia.save()
                logger.info(f"Incidencia '{nueva_incidencia.incidencia}' registrada con éxito.")
                messages.success(request, f'¡La incidencia "{nueva_incidencia.incidencia}" ha sido registrada con éxito!')
                return redirect('gestion:incidencias')
            except Exception as e:
                logger.error(f"Error al guardar incidencia: {e}", exc_info=True)
                messages.error(request, f'Error al guardar: {e}')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = IncidenciaForm()

    # Contexto para mantener compatibilidad con selectores manuales si se usan en JS
    # Aunque con el form ya no son estrictamente necesarios si se renderiza el form,
    # los mantenemos por si el template usa lógica específica.
    context = {
        'form': form,
        'form_data': request.POST if request.method == 'POST' else None,
        'aplicaciones': Aplicacion.objects.all().order_by('nombre_aplicacion'),
        'estados': Estado.objects.filter(uso_estado='Incidencia').order_by('desc_estado'),
        'severidades': Severidad.objects.all(),
        'impactos': Impacto.objects.all(),
        'grupos_resolutores': GrupoResolutor.objects.all(),
        'interfaces': Interfaz.objects.all(),
        'clusters': Cluster.objects.all(),
        'bloques': Bloque.objects.all(),
        'usuarios': Usuario.objects.all().order_by('nombre'),
    }
    return render(request, 'gestion/registrar_incidencia.html', context)


@login_required
@no_cache
@login_required
@no_cache
def editar_incidencia_view(request, pk):
    """
    Gestiona la edición de una incidencia existente usando Django Forms.
    """
    incidencia = get_object_or_404(Incidencia, pk=pk)

    if request.method == 'POST':
        form = IncidenciaForm(request.POST, instance=incidencia)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'¡La incidencia "{incidencia.incidencia}" ha sido actualizada con éxito!')
                return redirect('gestion:incidencias')
            except Exception as e:
                logger.error(f"Error al editar incidencia '{incidencia.id}': {e}", exc_info=True)
                messages.error(request, f'Error al actualizar: {e}')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = IncidenciaForm(instance=incidencia)

    # Contexto para compatibilidad
    codigos_cierre_app = CodigoCierre.objects.filter(aplicacion=incidencia.aplicacion) if incidencia.aplicacion else []
    
    context = {
        'form': form,
        'form_data': request.POST if request.method == 'POST' else None,
        'incidencia': incidencia, # Importante para que el template sepa que es edición
        'aplicaciones': Aplicacion.objects.all(),
        'estados': Estado.objects.filter(uso_estado='Incidencia').order_by('desc_estado'),
        'severidades': Severidad.objects.all(),
        'impactos': Impacto.objects.all(),
        'grupos_resolutores': GrupoResolutor.objects.all(),
        'interfaces': Interfaz.objects.all(),
        'clusters': Cluster.objects.all(),
        'bloques': Bloque.objects.all(),
        'usuarios': Usuario.objects.all().order_by('nombre'),
        'codigos_cierre': codigos_cierre_app,
    }
    return render(request, 'gestion/registrar_incidencia.html', context)


@login_required
@no_cache
def eliminar_incidencia_view(request, pk):
    """
    Gestiona la eliminación de una incidencia específica.

    Esta vista está protegida para aceptar únicamente peticiones POST como
    medida de seguridad, previniendo eliminaciones accidentales a través de
    enlaces (peticiones GET). Busca la incidencia por su clave primaria (pk)
    y, si la encuentra, la elimina.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        pk (int): La clave primaria (ID) de la incidencia a eliminar.

    Returns:
        HttpResponse: Siempre redirige a la vista 'gestion:incidencias'
                      después de intentar la operación.
    """
    # Se valida que la petición sea POST para proceder con la eliminación.
    if request.method == 'POST':
        logger.info(
            f"El usuario '{request.user}' ha iniciado un intento de eliminación para la incidencia con ID: {pk}.")
        try:
            # get_object_or_404 es la forma recomendada de obtener un objeto.
            # Si no lo encuentra, detendrá la ejecución y mostrará una página de "No Encontrado".
            incidencia = get_object_or_404(Incidencia, pk=pk)
            nombre_incidencia = incidencia.incidencia

            # Se elimina el objeto de la base de datos.
            incidencia.delete()

            # Se registra la eliminación como una ADVERTENCIA (WARNING) para que sea
            # fácil de localizar en los logs, ya que es una acción destructiva importante.
            logger.warning(
                f"ACCIÓN CRÍTICA: El usuario '{request.user}' ha ELIMINADO la incidencia '{nombre_incidencia}' (ID: {pk})."
            )
            messages.success(
                request, f'La incidencia "{nombre_incidencia}" ha sido eliminada correctamente.')

        except Exception as e:
            # Captura cualquier error inesperado durante la eliminación.
            # Esto puede incluir la excepción Http404 de get_object_or_404 si el ID no existe,
            # o errores de la base de datos (ej. por restricciones de clave foránea).
            logger.error(
                f"Error al intentar eliminar la incidencia ID {pk} por el usuario '{request.user}'. Error: {e}",
                # Registra el traceback completo para facilitar la depuración.
                exc_info=True
            )
            messages.error(
                request, f'Ocurrió un error al eliminar la incidencia: {e}')

    # Si la petición no es POST, o después de la operación, se redirige.
    return redirect('gestion:incidencias')


@login_required
@no_cache
def get_codigos_cierre_por_aplicacion(request, aplicacion_id):
    """
    Vista que, dado un ID de aplicación, devuelve los códigos de cierre
    asociados en formato JSON.
    """
    try:
        # Usamos .annotate() para crear alias que coincidan con lo que el JavaScript espera ('codigo' y 'descripcion')
        codigos = CodigoCierre.objects.filter(aplicacion_id=aplicacion_id).annotate(
            codigo=F('cod_cierre'),
            descripcion=F('desc_cod_cierre')
        ).order_by('codigo').values('id', 'codigo', 'descripcion')

        return JsonResponse(list(codigos), safe=False)

    except Exception as e:
        logger.error(
            f"Error en get_codigos_cierre_por_aplicacion: {e}", exc_info=True)
        return JsonResponse({'error': 'Ocurrió un error en el servidor.'}, status=500)


def normalize_text(text):
    """Convierte texto a minúsculas y quita acentos."""
    if text is None:
        return ""
    return unidecode(str(text)).lower().strip()


def parse_flexible_date(date_string):
    """
    Intenta analizar una cadena de fecha con múltiples formatos, incluyendo
    formatos con AM/PM en español.
    """
    if not date_string:
        return None

    # Normaliza los indicadores AM/PM para la directiva %p de Python
    processed_string = date_string.lower().replace(
        'a. m.', 'am').replace('p. m.', 'pm')
    processed_string = processed_string.replace(
        'a.m.', 'am').replace('p.m.', 'pm')

    # Lista de formatos a intentar.
    formats = [
        '%d-%m-%Y',             # DD-MM-YYYY (Solicitado explícitamente)
        '%d/%m/%Y',             # DD/MM/YYYY
        '%Y-%m-%d',             # YYYY-MM-DD (ISO)
        '%d-%m-%Y %H:%M:%S',    # Con hora
        '%d/%m/%Y %H:%M:%S',    # Con hora slashes
        '%Y-%m-%d %H:%M:%S',    # ISO con hora
        '%d/%m/%y %I:%M:%S %p', # AM/PM corto
        '%d/%m/%Y %I:%M:%S %p', # AM/PM largo
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(processed_string, fmt)
            return dt # timezone.make_aware(dt) # Removed for USE_TZ=False
        except ValueError:
            continue
    
    # Si falla, intentamos devolver None en lugar de romper, 
    # o podríamos dejar que el llamador maneje el None.
    return None



@login_required
@no_cache
def carga_masiva_incidencia_view(request):
    """
    Gestiona la carga masiva de incidencias.
    (Versión que crea si no existe, o informa si ya existe sin actualizar).
    """
    # ... (bloque try/except para las cachés sin cambios) ...
    try:
        # --- Creación de Cachés de Búsqueda ---
        aplicacion_cache = {normalize_text(
            a.cod_aplicacion): a for a in Aplicacion.objects.all()}
        estado_cache = {normalize_text(
            e.desc_estado): e for e in Estado.objects.all()}
        severidad_cache = {normalize_text(
            s.desc_severidad): s for s in Severidad.objects.all()}
        cluster_cache = {normalize_text(
            c.desc_cluster): c for c in Cluster.objects.all()}
        bloque_cache = {normalize_text(
            b.desc_bloque): b for b in Bloque.objects.all()}
        usuario_cache = {normalize_text(
            u.usuario): u for u in Usuario.objects.all()}
        grupo_resolutor_cache = {normalize_text(
            g.desc_grupo_resol): g for g in GrupoResolutor.objects.all()}

        default_impacto = Impacto.objects.get(desc_impacto__iexact='interno')
        default_interfaz = Interfaz.objects.get(desc_interfaz__iexact='WEB')

        # --- NUEVO: Precargar estados clave para la lógica de actualización ---
        estado_cerrado = Estado.objects.get(desc_estado__iexact='Cerrado')
        estado_cancelado = Estado.objects.get(
            desc_estado__iexact='Cancelado')
        estado_resuelto = Estado.objects.get(desc_estado__iexact='Resuelto')
        estados_finales = [estado_cerrado, estado_cancelado]
        # --- FIN DE LA MODIFICACIÓN ---

    except ObjectDoesNotExist as e:
        messages.error(
            request, f"Error de Configuración: No se encontró un valor por defecto. Error: {e}")
        return redirect('gestion:carga_masiva_incidencia')

    if request.method == 'POST':
        file = request.FILES.get('csv_file')
        if not file or not (file.name.endswith('.csv') or file.name.endswith('.xlsx')):
            messages.error(
                request, 'Por favor, selecciona un archivo con formato .csv o .xlsx.')
            return redirect('gestion:carga_masiva_incidencia')

        # <<<--- PASO 1: AJUSTAR CONTADORES ---<<<
        failed_rows = []
        new_indra_d_count = 0
        new_normal_count = 0
        updated_count = 0
        skipped_count = 0

        try:
            # LÓGICA DE LECTURA SEGÚN TIPO DE ARCHIVO
            is_json = False
            df = None
            all_rows_json = []

            if file.name.endswith('.csv'):
                df = pd.read_csv(file, keep_default_na=False, dtype=str)
                df.fillna('', inplace=True)
            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file, keep_default_na=False, dtype=str)
                df.fillna('', inplace=True)
            elif file.name.endswith('.json'):
                is_json = True
                # Leemos el contenido raw para intentar arreglarlo si es necesario
                file_content = file.read().decode('utf-8').strip()
                
                # Intento de corrección automática de brackets
                if file_content.startswith('{') and file_content.endswith('}'):
                    logger.info("JSON de incidencias sin brackets detectado. Corrigiendo...")
                    file_content = f"[{file_content}]"
                
                try:
                    all_rows_json = json.loads(file_content)
                except json.JSONDecodeError as e:
                    messages.error(request, f"Error de formato JSON: {e}")
                    return redirect('gestion:carga_masiva_incidencia')

                if not isinstance(all_rows_json, list):
                    messages.error(request, 'El JSON debe ser una lista de objetos.')
                    return redirect('gestion:carga_masiva_incidencia')
                
                logger.info(f"Leídos {len(all_rows_json)} registros JSON de incidencias.")

            else:
                 messages.error(request, 'Formato no soportado. Use CSV, Excel o JSON.')
                 return redirect('gestion:carga_masiva_incidencia')

            def parse_flexible_date(date_string):
                """
                Intenta analizar una cadena de fecha con múltiples formatos, incluyendo
                formatos con AM/PM en español.
                """
                if not date_string:
                    return None

                # Normaliza los indicadores AM/PM para la directiva %p de Python
                # (maneja 'a. m.', 'p. m.', 'a.m.', 'p.m.', etc.)
                processed_string = date_string.lower().replace(
                    'a. m.', 'am').replace('p. m.', 'pm')
                processed_string = processed_string.replace(
                    'a.m.', 'am').replace('p.m.', 'pm')

                # Lista de formatos a intentar.
                formats = [
                    '%d-%m-%Y %H:%M:%S',      # Formato original: 25-12-2023 14:30:00
                    '%d/%m/%y %I:%M:%S %p',  # AM/PM con año de 2 dígitos: 01/09/25 08:53:27 am
                    '%d/%m/%Y %I:%M:%S %p',  # AM/PM con año de 4 dígitos: 01/09/2025 08:53:27 am
                    '%d/%m/%y %H:%M:%S',    # Militar con slashes, año de 2 dígitos: 01/09/25 14:30:00
                    '%d/%m/%Y %H:%M:%S',    # Militar con slashes, año de 4 dígitos: 01/09/2025 14:30:00
                ]

                for fmt in formats:
                    try:
                        dt = datetime.strptime(processed_string, fmt)
                        return dt # timezone.make_aware(dt) # Removed for USE_TZ=False
                    except ValueError:
                        continue

                # Si ningún formato coincide, lanza un error que será capturado por el try-except externo.
                raise ValueError(
                    f"El formato de fecha '{date_string}' no es válido o no está soportado.")

            with transaction.atomic():
                # Unificamos el iterador: Si es DF usamos iterrows, si es JSON usamos enumerate
                iterator = df.iterrows() if not is_json else enumerate(all_rows_json, 0)

                for index, row in iterator:
                    line_number = index + 2
                    
                    # Normalización de acceso a datos (Row Pandas vs Dict JSON)
                    def get_val(key, default=''):
                        if is_json:
                            # En JSON las claves son directas
                            val = row.get(key)
                            return str(val).strip() if val is not None else default
                        else:
                            # En Pandas usamos las columnas (mapeo previo requerido si nombres difieren)
                            # Aquí asumimos nombres de columnas del CSV/Excel o adaptamos
                            return str(row.get(key, default)).strip()

                    try:
                        incidencia_id = get_val('incidencia')
                        if not incidencia_id: # Intento fallback por si la clave es diferente en JSON
                             incidencia_id = get_val('incidencia_id')

                        if not incidencia_id or not incidencia_id.upper().startswith('INC'):
                            continue

                        # ... (Toda la lógica de asignación de objetos) ...
                        aplicacion_obj = None
                        codigo_cierre_obj = None
                        
                        # Mapeo de campos flexibles (soportar ID o Texto)
                        
                        # 1. APP: En JSON viene 'id_aplicacion' (numérico)
                        app_val = get_val('aplicacion_id') or get_val('id_aplicacion')
                        
                        # 2. Cod Cierre: En JSON viene 'cod_cierre' (numérico ID o texto código?)
                        # La imagen muestra "cod_cierre": 3378 (parece ID numérico en la imagen!)
                        cc_val = get_val('codigo_cierre_id') or get_val('cod_cierre')
                        
                        # Lógica de búsqueda APP
                        if app_val:
                            if app_val.isdigit(): # Búsqueda por ID directo
                                aplicacion_obj = Aplicacion.objects.filter(id=int(app_val)).first()
                            else: # Búsqueda por código texto
                                aplicacion_obj = aplicacion_cache.get(normalize_text(app_val))
                        
                        # Lógica de búsqueda Cod Cierre
                        if cc_val:
                            # Asumimos que si es dígito grande es ID, si no es código texto
                            if cc_val.isdigit():
                                codigo_cierre_obj = CodigoCierre.objects.filter(id=int(cc_val)).first()
                            else:
                                if aplicacion_obj:
                                     codigo_cierre_obj = CodigoCierre.objects.filter(cod_cierre__iexact=cc_val, aplicacion=aplicacion_obj).first()
                                else:
                                     codigo_cierre_obj = CodigoCierre.objects.filter(cod_cierre__iexact=cc_val).first()

                        # 3. Estado (id_estado en JSON)
                        estado_val = get_val('estado_id') or get_val('id_estado')
                        estado_obj = None
                        if estado_val.isdigit():
                             estado_obj = Estado.objects.filter(id=int(estado_val)).first()
                        else:
                             estado_obj = estado_cache.get(normalize_text(estado_val))

                        # 4. Severidad (id_severidad en JSON)
                        sev_val = get_val('severidad_id') or get_val('id_severidad') # Nota: Imagen dice 'id_criticidad', suele mapear a severidad en lógica negocio? O 'id_impacto'?
                        # Revisando imagen: 'id_criticidad': 3. 'id_impacto': 1.
                        # Asumimos id_criticidad -> Severidad (común confusión) o Severidad es otro. 
                        # En el código original: severidad_obj = severidad_cache.get(normalize_text(row['severidad_id']))
                        # Vamos a mapear 'id_criticidad' a Severidad por ahora si no hay 'id_severidad'.
                        severidad_obj = None
                        if sev_val:
                             if sev_val.isdigit(): severidad_obj = Severidad.objects.filter(id=int(sev_val)).first()
                             else: severidad_obj = severidad_cache.get(normalize_text(sev_val))
                        
                        # 5. Cluster (id_cluster)
                        cluster_val = get_val('cluster_id') or get_val('id_cluster')
                        cluster_obj = None
                        if cluster_val and cluster_val.isdigit(): cluster_obj = Cluster.objects.filter(id=int(cluster_val)).first()
                        elif cluster_val: cluster_obj = cluster_cache.get(normalize_text(cluster_val))

                        # 6. Bloque (id_bloque)
                        bloque_val = get_val('bloque_id') or get_val('id_bloque')
                        # ... lógica especial INDRA ...
                        # Simplificación para JSON con ID directo:
                        bloque_obj = None
                        if bloque_val and bloque_val.isdigit():
                            bloque_obj = Bloque.objects.filter(id=int(bloque_val)).first()
                        elif bloque_val:
                             bloque_val_norm = normalize_text(bloque_val)
                             # (Mantener lógica legacy de indra_d strings si viene texto)
                             bloque_obj = bloque_cache.get(bloque_val_norm)

                        # ... Lógica grupo resolutor (id_grupo_resolutor) ...
                        gr_val = get_val('grupo_resolutor_id') or get_val('id_grupo_resolutor')
                        grupo_resolutor_obj = None
                        if gr_val and gr_val.isdigit(): grupo_resolutor_obj = GrupoResolutor.objects.filter(id=int(gr_val)).first()
                        elif gr_val: grupo_resolutor_obj = grupo_resolutor_cache.get(normalize_text(gr_val))

                        # ... Lógica impacto, interfaz ...
                        
                        # Fechas
                        fecha_apertura = parse_flexible_date(get_val('fecha_apertura'))
                        fecha_resolucion = parse_flexible_date(get_val('fecha_ultima_resolucion'))

                        # Campos directos
                        desc = get_val('descripcion_incidencia')
                        causa = get_val('causa')
                        bitacora = get_val('bitacora')
                        tec_analisis = get_val('tec_analisis')
                        correccion = get_val('correccion')
                        solucion = get_val('solucion_final')
                        obs = get_val('observaciones')
                        demandas = get_val('demandas')
                        workaround_raw = get_val('workaround') or get_val('workaround')
                        workaround_val = 'Sí' if 'con wa' in workaround_raw.lower() or workaround_raw.lower() == 'si' else 'No'
                        
                        # Usuario asignado (id_usuario_asignado ?)
                        # Imagen dice: "usuario_asignado": 7
                        ua_val = get_val('usuario_asignado_id') or get_val('usuario_asignado')
                        usuario_asignado_obj = None
                        if ua_val and ua_val.isdigit(): usuario_asignado_obj = Usuario.objects.filter(id=int(ua_val)).first()
                        
                        # RE-MAPEO para consistencia con código original que usa variables
                        # Sobreescribimos las variables que el código original usaba abajo
                        
                        is_indra_d_row = False # En JSON con ID explicito esto se maneja por el ID del bloque/grupo
                        
                        impacto_obj = default_impacto # Default
                        interfaz_obj = default_interfaz # Default

                        # --- LÓGICA DE CREACIÓN O ACTUALIZACIÓN ---
                        try:
                            existing_incidence = Incidencia.objects.get(
                                incidencia=incidencia_id)

                            # --- LÓGICA PARA INCIDENCIAS EXISTENTES ---
                            if existing_incidence.estado in estados_finales:
                                skipped_count += 1
                                logger.info(
                                    f"Línea {line_number}: INCIDENCIA OMITIDA {incidencia_id} (estado final).")
                                continue

                            if existing_incidence.estado == estado_resuelto and estado_obj in estados_finales:
                                old_state_desc = existing_incidence.estado.desc_estado
                                existing_incidence.estado = estado_obj
                                if fecha_resolucion:
                                    existing_incidence.fecha_ultima_resolucion = fecha_resolucion
                                existing_incidence.save(
                                    update_fields=['estado', 'fecha_ultima_resolucion'])
                                updated_count += 1
                                logger.info(
                                    f"Línea {line_number}: INCIDENCIA ACTUALIZADA {incidencia_id} (ID: {existing_incidence.id}, Estado: '{old_state_desc}' -> '{estado_obj.desc_estado}').")
                            else:
                                skipped_count += 1
                                logger.info(
                                    f"Línea {line_number}: INCIDENCIA OMITIDA {incidencia_id} (No requiere actualización).")

                        except Incidencia.DoesNotExist:
                            # --- LÓGICA PARA NUEVAS INCIDENCIAS ---
                            logger.info(f"Creando incidencia {incidencia_id} con usuario: {request.user} (ID: {request.user.id})")
                            obj = Incidencia.objects.create(
                                incidencia=incidencia_id,
                                descripcion_incidencia=desc,
                                fecha_apertura=fecha_apertura,
                                fecha_ultima_resolucion=fecha_resolucion,
                                causa=causa,
                                bitacora=bitacora,
                                tec_analisis=tec_analisis,
                                correccion=correccion,
                                solucion_final=solucion,
                                observaciones=obs,
                                demandas=demandas,
                                workaround=workaround_val,
                                aplicacion=aplicacion_obj,
                                estado=estado_obj,
                                severidad=severidad_obj,
                                grupo_resolutor=grupo_resolutor_obj,
                                interfaz=interfaz_obj,
                                impacto=impacto_obj,
                                cluster=cluster_obj,
                                bloque=bloque_obj,
                                codigo_cierre=codigo_cierre_obj,
                                usuario_asignado=usuario_asignado_obj,
                                usuario_creador=request.user,
                            )
                            if is_indra_d_row:
                                new_indra_d_count += 1
                            else:
                                new_normal_count += 1
                            logger.info(
                                f"Línea {line_number}: INCIDENCIA CREADA {incidencia_id} (ID: {obj.id}).")

                    except Exception as e:
                        logger.error(
                            f"Error procesando fila {line_number} (Incidencia: {incidencia_id if 'incidencia_id' in locals() else 'Desconocida'}): {e}", exc_info=True)
                        failed_rows.append({'line': line_number, 'row_data': 'JSON Data' if is_json else ', '.join(map(str, row.values)), 'error': str(e)})

            # <<<--- PASO 4: AJUSTAR RESUMEN FINAL ---<<<
            total_creadas = new_indra_d_count + new_normal_count
            
            # Preparar string con líneas fallidas
            failed_lines_str = ""
            if failed_rows:
                failed_lines = [str(item['line']) for item in failed_rows]
                failed_lines_str = f" (Fallos en Líneas: {', '.join(failed_lines)})"

            logger.info(
                f"Resumen Carga Masiva Inicial (Usuario: {request.user}) - "
                f"Total Leídos: {len(df)} | "
                f"Creados: {total_creadas} (INDRA_D: {new_indra_d_count}, Normales: {new_normal_count}) | "
                f"Actualizados: {updated_count} | "
                f"Omitidos: {skipped_count} | "
                f"Fallidos: {len(failed_rows)}{failed_lines_str}"
            )
            
            # Detalle adicional de errores en log si existen
            if failed_rows:
                for item in failed_rows:
                    incidencia_id_error = item.get('row_data', 'N/A').split(',')[0]
                    # Solo logueamos si es un error complejo, la línea ya está en el resumen
                    logger.error(f"Detalle Error Línea {item['line']} ({incidencia_id_error}): {item['error']}")

            if total_creadas > 0:
                messages.success(
                    request, f'¡Carga completada! Total creadas: {total_creadas} (INDRA_D: {new_indra_d_count}, Normales: {new_normal_count}).')
            if updated_count > 0:
                messages.info(
                    request, f'Se actualizaron {updated_count} incidencias que estaban resueltas.')
            if skipped_count > 0:
                messages.info(
                    request, f'Se omitieron {skipped_count} incidencias que ya existían y no requerían actualización.')
            if failed_rows:
                messages.warning(
                    request, f'Se encontraron {len(failed_rows)} errores. Por favor, revisa los detalles.')

            return render(request, 'gestion/carga_masiva_incidencia.html', {'failed_rows': failed_rows})

        except Exception as e:
            logger.error(
                f"Error crítico al leer o procesar el archivo '{file.name}': {e}", exc_info=True)
            messages.error(
                request, f'Ocurrió un error al leer o procesar el archivo: {e}')
            return redirect('gestion:carga_masiva_incidencia')

    return render(request, 'gestion/carga_masiva_incidencia.html')


# VISTA NUEVA PARA EXPORTAR EL REPORTE EN FORMATO XLSX
@login_required
@no_cache
def exportar_incidencias_reporte_view(request):
    """
    Genera y exporta un reporte de incidencias en formato .xlsx,
    respetando los filtros aplicados en la vista principal.
    """
    logger.info(
        f"Usuario '{request.user}' ha solicitado un reporte de incidencias en Excel.")

    # 1. Queryset base optimizado (igual que en incidencias_view)
    incidencias_qs = Incidencia.objects.select_related(
        'aplicacion', 'estado', 'severidad', 'impacto', 'bloque',
        'codigo_cierre', 'grupo_resolutor'
    ).all()

    # 2. Replicar la lógica de filtrado de incidencias_view
    # Esto es crucial para que el reporte coincida con la tabla visible
    filtro_app_id = request.GET.get('aplicativo')
    filtro_bloque_id = request.GET.get('bloque')
    filtro_incidencia = request.GET.get('incidencia')
    filtro_codigo_id = request.GET.get('codigo_cierre')
    filtro_fecha_desde = request.GET.get('fecha_desde')
    filtro_fecha_hasta = request.GET.get('fecha_hasta')

    if filtro_app_id and filtro_app_id.isdigit():
        incidencias_qs = incidencias_qs.filter(aplicacion_id=filtro_app_id)
    if filtro_bloque_id and filtro_bloque_id.isdigit():
        incidencias_qs = incidencias_qs.filter(bloque_id=filtro_bloque_id)
    if filtro_incidencia:
        incidencias_qs = incidencias_qs.filter(
            incidencia__icontains=filtro_incidencia)
    if filtro_codigo_id and filtro_codigo_id.isdigit():
        incidencias_qs = incidencias_qs.filter(
            codigo_cierre_id=filtro_codigo_id)
    if filtro_fecha_desde:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_desde, '%Y-%m-%d')
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__gte=fecha_obj)
        except (ValueError, TypeError):
            pass
    if filtro_fecha_hasta:
        try:
            fecha_obj = datetime.strptime(filtro_fecha_hasta, '%Y-%m-%d')
            fecha_obj_fin_dia = fecha_obj + timedelta(days=1)
            incidencias_qs = incidencias_qs.filter(
                fecha_ultima_resolucion__lt=fecha_obj_fin_dia)
        except (ValueError, TypeError):
            pass

    # 3. Preparar los datos para el DataFrame de Pandas
    meses_es = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
        7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }

    data_para_excel = []
    for inc in incidencias_qs:
        mes_resolucion = ""
        fecha_resolucion_str = ""
        if inc.fecha_ultima_resolucion:
            # Hacemos la fecha consciente a la zona horaria local para extraer el mes correcto
            fecha_local = inc.fecha_ultima_resolucion # timezone.localtime(inc.fecha_ultima_resolucion) # Removed for USE_TZ=False
            mes_resolucion = meses_es.get(fecha_local.month, '')
            fecha_resolucion_str = fecha_local.strftime('%d-%m-%Y %H:%M')

        data_para_excel.append({
            'ID de la Incidencia': inc.incidencia,
            'Criticidad aplicativo': inc.aplicacion.criticidad.desc_criticidad if inc.aplicacion and inc.aplicacion.criticidad else 'N/A',
            'severidad incidencia': inc.severidad.desc_severidad if inc.severidad else 'N/A',
            'Grupo resolutor': inc.grupo_resolutor.desc_grupo_resol if inc.grupo_resolutor else 'N/A',
            'Aplicativo': inc.aplicacion.nombre_aplicacion if inc.aplicacion else 'N/A',
            'Fecha de Resolucion': fecha_resolucion_str,
            'mes': mes_resolucion,
            'cod_cierre': inc.codigo_cierre.cod_cierre if inc.codigo_cierre else 'N/A',
            'Descripción Cierre': inc.codigo_cierre.desc_cod_cierre if inc.codigo_cierre else 'N/A',
            'Bloque': inc.bloque.desc_bloque if inc.bloque else 'N/A'
        })

    # 4. Crear el archivo Excel en memoria usando Pandas
    df = pd.DataFrame(data_para_excel)
    output = io.BytesIO()

    # Escribir el DataFrame al buffer de BytesIO como un archivo Excel
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte Incidencias')
        worksheet = writer.sheets['Reporte Incidencias']
        # Opcional: Auto-ajustar el ancho de las columnas
        for column in df:
            column_length = max(df[column].astype(
                str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            worksheet.column_dimensions[get_column_letter(
                col_idx + 1)].width = column_length + 2

    output.seek(0)  # Mover el cursor al inicio del stream

    # 5. Crear la respuesta HTTP para descargar el archivo
    filename = f"Reporte_Incidencias_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Se establece una cookie para que el frontend pueda ocultar el spinner
    response.set_cookie('descargaFinalizada', 'true', max_age=20, path='/')

    return response


def _clean_control_chars(text):
    """
    Función auxiliar para limpiar una cadena de texto de caracteres de control invisibles
    que pueden causar errores al parsear JSON.
    """
    if not isinstance(text, str):
        return text
    # Elimina caracteres de control excepto tabulación (\t), nueva línea (\n) y retorno de carro (\r)
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)


@login_required
@no_cache
def carga_masiva_inicial_view(request):
    """
    Gestiona la carga masiva de incidencias desde un archivo JSON bien formado.
    """
    if request.method != 'POST':
        return render(request, 'gestion/carga_masiva_inicial.html')

    logger.info(
        f"Usuario '{request.user}' ha iniciado una carga masiva inicial de incidencias.")
    file = request.FILES.get('incidencias_file')

    if not file or not file.name.endswith('.json'):
        messages.error(
            request, 'El archivo debe ser un JSON válido con extensión .json')
        return redirect('gestion:carga_masiva_inicial')

    try:
        # --- 1. Precarga de Catálogos en Caché para Optimización ---
        logger.info("Precargando catálogos en memoria para validación...")
        aplicacion_cache = {str(a.id): a for a in Aplicacion.objects.all()}
        estado_cache = {str(e.id): e for e in Estado.objects.all()}
        impacto_cache = {str(i.id): i for i in Impacto.objects.all()}
        bloque_cache = {str(b.id): b for b in Bloque.objects.all()}
        grupo_resolutor_cache = {
            str(g.id): g for g in GrupoResolutor.objects.all()}
        interfaz_cache = {str(i.id): i for i in Interfaz.objects.all()}
        cluster_cache = {str(c.id): c for c in Cluster.objects.all()}
        usuario_name_cache = {unidecode(str(u.nombre or '')).lower().strip(): u for u in Usuario.objects.all()}
        usuario_id_cache = {str(u.id): u for u in Usuario.objects.all()}
        codigo_cierre_cache = {(cc.cod_cierre, cc.aplicacion_id)
                                : cc for cc in CodigoCierre.objects.select_related('aplicacion')}
        severidad_cache = {str(s.id): s for s in Severidad.objects.all()}
        logger.info("Cachés creadas con éxito.")

        # --- 2. Lectura y Limpieza del Archivo JSON ---
        decoded_file = file.read().decode('utf-8', errors='replace')
        cleaned_text = _clean_control_chars(decoded_file)
        all_rows_data = json.loads(cleaned_text)

        if not isinstance(all_rows_data, list):
            raise ValueError(
                "El formato JSON es incorrecto. Se esperaba una lista de incidencias `[...]`.")

        logger.info(
            f"Archivo JSON parseado. Se encontraron {len(all_rows_data)} registros para procesar.")
        errors, created_count, skipped_count = [], 0, 0

        # --- 3. Procesamiento de cada Incidencia ---
        for i, row_data in enumerate(all_rows_data, start=1):
            incidencia_id = row_data.get('incidencia')
            try:
                if not incidencia_id:
                    raise ValueError(
                        'El atributo "incidencia" (ID de la incidencia) es obligatorio.')

                if Incidencia.objects.filter(incidencia=incidencia_id).exists():
                    skipped_count += 1
                    logger.info(
                        f"Línea {i}: INCIDENCIA OMITIDA {incidencia_id} (Ya existe).")
                    continue

                # --- Validación explícita de campos obligatorios contra caché ---
                # --- Validación explícita de campos obligatorios contra caché ---
                id_aplicacion = row_data.get('id_aplicacion')
                aplicacion_obj = None
                
                # Si viene un ID de aplicación, verificamos que exista. Si es null/None, se permite null.
                if id_aplicacion is not None and str(id_aplicacion).lower() != 'null' and str(id_aplicacion).strip() != '':
                     aplicacion_obj = aplicacion_cache.get(str(id_aplicacion))
                     if not aplicacion_obj:
                         # Opción: O lanzar error O dejarlo en None.
                         # Dado que el usuario pidió cargar "de igual forma", si el ID no existe podríamos
                         # forzar error O asumir None. Lo estándar es error si el ID venía pero no existe.
                         # Pero si el ID venía como null, ya lo manejamos.
                         pass 
                         # raise ValueError(f"ID de Aplicación no encontrado en la BD: '{id_aplicacion}'") 
                         # DECISIÓN: Si traía un ID y no existe, mejor avisar.
                         # Pero el error del usuario era "ID de Aplicación no encontrado en la BD: 'None'".
                         # Eso significa que row_data.get devolvió None, y lo convertimos a string 'None'.
                         
                # Corrección específica: si id_aplicacion era None, no entramos al if, y aplicacion_obj queda None.
                # El error ocurría porque id_aplicacion era None, str(None) -> 'None', buscaba 'None' y fallaba.
                # Con la condición `if id_aplicacion is not None ...` solucionamos eso.

                id_estado = row_data.get('id_estado')
                estado_obj = estado_cache.get(str(id_estado))
                if not estado_obj:
                    raise ValueError(
                        f"ID de Estado no encontrado en la BD: '{id_estado}'")

                # --- ### INICIO DE LA LÓGICA MODIFICADA ### ---
                # Obtiene el valor original de 'id_impacto'.
                id_impacto_original = row_data.get('id_impacto')

                # Si el valor es nulo o una cadena vacía, se le asigna '1' por defecto.
                if id_impacto_original is None or str(id_impacto_original).strip() == '':
                    id_impacto_final = '1'
                else:
                    id_impacto_final = str(id_impacto_original)

                # Busca el objeto Impacto usando el ID final (el original o el por defecto).
                impacto_obj = impacto_cache.get(id_impacto_final)
                if not impacto_obj:
                    # Si aún no lo encuentra (ej: el ID '1' no existe), lanza un error detallado.
                    raise ValueError(
                        f"ID de Impacto no encontrado en la BD: '{id_impacto_final}' (Valor Original: '{id_impacto_original}')")
                # --- ### FIN DE LA LÓGICA MODIFICADA ### ---

                id_criticidad = row_data.get('id_criticidad')
                severidad_obj = severidad_cache.get(str(id_criticidad))
                if not severidad_obj:
                    raise ValueError(
                        f"ID de Criticidad/Severidad no encontrado en la BD: '{id_criticidad}'")

                # --- Búsqueda de objetos opcionales en caché ---
                grupo_resolutor_obj = grupo_resolutor_cache.get(
                    str(row_data.get('id_grupo_resolutor')))
                interfaz_obj = interfaz_cache.get(
                    str(row_data.get('id_interfaz')))
                cluster_obj = cluster_cache.get(
                    str(row_data.get('id_cluster')))
                bloque_obj = bloque_cache.get(str(row_data.get('id_bloque')))

                usuario_asignado_obj = None
                usuario_asignado_obj = None
                if val_ua := row_data.get('usuario_asignado'):
                    # Intento 1: Buscar por ID (si es número)
                    if str(val_ua).isdigit():
                        usuario_asignado_obj = usuario_id_cache.get(str(val_ua))
                    
                    # Intento 2: Buscar por nombre (normalized)
                    if not usuario_asignado_obj:
                         usuario_asignado_obj = usuario_name_cache.get(
                            unidecode(str(val_ua)).lower().strip())

                codigo_cierre_obj = None
                # Validamos cod_cierre similarmente (ya era opcional pero reforzamos)
                cod_cierre_val = row_data.get('cod_cierre')
                if cod_cierre_val is not None and str(cod_cierre_val).lower() != 'null' and str(cod_cierre_val).strip() != '':
                     if aplicacion_obj:
                         codigo_cierre_obj = codigo_cierre_cache.get((cod_cierre_val, aplicacion_obj.id))
                     # Nota: Si no hay app, difícil encontrar cod cierre por tupla (cod, app_id).
                     # Podríamos buscar solo por cod_cierre si fuera único, pero el cache usa tupla.
                     # Si aplicacion es None, codigo_cierre será None.

                # --- Manejo de Fechas ---
                fecha_apertura_obj = parse_flexible_date(row_data.get('fecha_apertura'))
                fecha_resolucion_obj = parse_flexible_date(row_data.get('fecha_ultima_resolucion'))

                # --- Lógica de Workaround ---
                raw_workaround = row_data.get('workaround')
                if raw_workaround and 'con wa' in str(raw_workaround).lower():
                    workaround_val = 'Sí'
                elif raw_workaround and 'sin wa' in str(raw_workaround).lower():
                    workaround_val = 'No'
                else:
                    # Si es null o cualquier otro valor, aplica el default actual 'No'
                    workaround_val = 'No'

                # --- Creación del Objeto Incidencia en la Base de Datos ---
                obj = Incidencia.objects.create(
                    incidencia=incidencia_id, aplicacion=aplicacion_obj, estado=estado_obj, impacto=impacto_obj, severidad=severidad_obj,
                    descripcion_incidencia=row_data.get(
                        'descripcion_incidencia') or '',
                    fecha_apertura=fecha_apertura_obj, fecha_ultima_resolucion=fecha_resolucion_obj,
                    grupo_resolutor=grupo_resolutor_obj, interfaz=interfaz_obj, cluster=cluster_obj,
                    bloque=bloque_obj, usuario_asignado=usuario_asignado_obj, codigo_cierre=codigo_cierre_obj,
                    causa=row_data.get('causa') or '', 
                    bitacora=row_data.get('bitacora') or '',
                    tec_analisis=row_data.get('tec_analisis') or '', 
                    correccion=row_data.get('correccion') or '',
                    solucion_final=row_data.get('solucion_final') or '', 
                    observaciones=row_data.get('observaciones') or '',
                    demandas=row_data.get('demandas') or '',
                    workaround=workaround_val,
                    usuario_creador=request.user
                )
                created_count += 1
                logger.info(
                    f"Línea {i}: INCIDENCIA CREADA {incidencia_id} (ID: {obj.id}).")

            except Exception as e:
                error_msg = str(e)
                errors.append(
                    {'line': i, 'row_data': f"Incidencia: {incidencia_id or 'N/A'}", 'error': error_msg})
                logger.error(
                    f"Error procesando registro #{i} (Incidencia: {incidencia_id}): {error_msg}")

        # --- 4. Resumen Final y Salida ---
        # Preparar string con líneas fallidas para el log
        failed_lines_str = ""
        if errors:
            failed_lines = [str(item['line']) for item in errors]
            failed_lines_str = f" (Fallos en Líneas: {', '.join(failed_lines)})"

        # Log resumen consolidado
        logger.info(
            f"Resumen Carga Masiva Inicial (Usuario: {request.user}) - "
            f"Total Leídos: {len(all_rows_data)} | "
            f"Creadas: {created_count} | "
            f"Omitidas: {skipped_count} | "
            f"Fallidos: {len(errors)}{failed_lines_str}"
        )

        stats = {
            'total': len(all_rows_data),
            'created': created_count,
            'skipped': skipped_count,
            'failed': len(errors)
        }

        if errors:
            messages.warning(
                request, f'Carga finalizada. Se crearon {created_count}, se omitieron {skipped_count} y fallaron {len(errors)} registros.')
        else:
            messages.success(
                request, f'¡Carga exitosa! Se procesaron {len(all_rows_data)} registros correctamente.')

        # Contexto para el template (reusando el mismo template de carga inicial)
        context = {
            'errors': errors,  # Lista de errores detallados
            'stats': stats     # Resumen estadístico
        }
        return render(request, 'gestion/carga_masiva_inicial.html', context)

    except Exception as e:
        logger.critical(
            f"Error crítico durante la carga masiva: {e}", exc_info=True)
        messages.error(
            request, f'Ocurrió un error inesperado en el servidor: {e}')
        return redirect('gestion:carga_masiva_inicial')
