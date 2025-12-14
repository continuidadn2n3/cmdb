# gestion/views/aplicaciones.py

import json
import csv
from django.http import HttpResponse
from django.contrib import messages, auth
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .utils import no_cache, logger
from ..models import Aplicacion, Bloque, Criticidad, Estado
from ..forms import AplicacionForm
from django.db import utils as db_utils


@login_required
@no_cache
def aplicaciones_view(request):
    """
    Renderiza la página principal del mantenedor de aplicaciones.

    Esta vista se encarga de:
    1.  Obtener y mostrar una lista de todas las aplicaciones.
    2.  Procesar y aplicar los filtros de búsqueda enviados por el usuario
        a través de una petición GET.
    3.  Poblar los menús desplegables (<select>) del formulario de filtros.
    4.  Pasar los datos filtrados y la información necesaria a la plantilla.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Una respuesta HTTP que renderiza la plantilla
                      'gestion/aplicaciones.html' con el contexto necesario.

    Context:
        'lista_de_aplicaciones' (QuerySet<Aplicacion>): El conjunto de aplicaciones
            resultante después de aplicar los filtros.
        'total_registros' (int): El número total de aplicaciones existentes en la BD.
        'todos_los_bloques' (QuerySet<Bloque>): Lista de todos los bloques para el filtro.
        'todas_las_criticidades' (QuerySet<Criticidad>): Lista de todas las
            criticidades para el filtro.
        'todos_los_estados' (QuerySet<Estado>): Lista de todos los estados de tipo
            'Aplicacion' para el filtro.
    """
    # --- 1. Inicio y Registro de Acceso ---
    logger.info(
        f"El usuario '{request.user}' ha accedido a la vista de aplicaciones.")

    # --- 2. Queryset Base ---
    # Se utiliza select_related para optimizar la consulta, precargando los datos
    # de las tablas relacionadas (Bloque, Criticidad, Estado) en una sola consulta SQL.
    aplicaciones_qs = Aplicacion.objects.select_related(
        'bloque', 'criticidad', 'estado').all()

    # --- 3. Procesamiento de Filtros ---
    # Se recogen los parámetros de la URL. Si no existen, .get() devuelve None.
    filtro_nombre = request.GET.get('nombre_app')
    filtro_codigo = request.GET.get('codigo_app')
    filtro_bloque_id = request.GET.get('bloque')
    filtro_criticidad_id = request.GET.get('criticidad')
    filtro_estado_id = request.GET.get('estado')

    # Lista para registrar qué filtros se están usando en esta petición.
    filtros_aplicados = []

    if filtro_nombre:
        aplicaciones_qs = aplicaciones_qs.filter(
            nombre_aplicacion__icontains=filtro_nombre)
        filtros_aplicados.append(f"nombre='{filtro_nombre}'")

    if filtro_codigo:
        aplicaciones_qs = aplicaciones_qs.filter(
            cod_aplicacion__icontains=filtro_codigo)
        filtros_aplicados.append(f"código='{filtro_codigo}'")

    if filtro_bloque_id and filtro_bloque_id.isdigit():
        aplicaciones_qs = aplicaciones_qs.filter(bloque_id=filtro_bloque_id)
        filtros_aplicados.append(f"bloque_id='{filtro_bloque_id}'")

    if filtro_criticidad_id and filtro_criticidad_id.isdigit():
        aplicaciones_qs = aplicaciones_qs.filter(
            criticidad_id=filtro_criticidad_id)
        filtros_aplicados.append(f"criticidad_id='{filtro_criticidad_id}'")

    if filtro_estado_id and filtro_estado_id.isdigit():
        aplicaciones_qs = aplicaciones_qs.filter(estado_id=filtro_estado_id)
        filtros_aplicados.append(f"estado_id='{filtro_estado_id}'")

    # Si se aplicó al menos un filtro, se registra en el log.
    if filtros_aplicados:
        logger.info(
            f"Búsqueda de aplicaciones con filtros: {', '.join(filtros_aplicados)}.")

    # Se registra cuántos resultados se encontraron con los filtros actuales.
    num_resultados = aplicaciones_qs.count()
    logger.info(f"La consulta ha devuelto {num_resultados} aplicaciones.")

    # --- 4. Preparación del Contexto para la Plantilla ---
    # Se obtienen los datos necesarios para poblar los menús desplegables de los filtros.
    todos_los_bloques = Bloque.objects.all().order_by('desc_bloque')
    todas_las_criticidades = Criticidad.objects.all().order_by('desc_criticidad')
    todos_los_estados = Estado.objects.filter(
        uso_estado=Estado.UsoChoices.APLICACION).order_by('desc_estado')

    # Se obtiene el conteo total de aplicaciones en el sistema para mostrarlo como estadística.
    total_registros = Aplicacion.objects.count()

    context = {
        'lista_de_aplicaciones': aplicaciones_qs,
        'total_registros': total_registros,
        'todos_los_bloques': todos_los_bloques,
        'todas_las_criticidades': todas_las_criticidades,
        'todos_los_estados': todos_los_estados,
    }

    # --- 5. Renderizado Final ---
    return render(request, 'gestion/aplicaciones.html', context)


@no_cache
@login_required
@no_cache
@login_required
def registrar_aplicacion_view(request):
    """
    Gestiona el registro de una nueva aplicación usando Django Forms.
    """
    if request.method == 'POST':
        logger.info(f"El usuario '{request.user}' intenta registrar una aplicación.")
        form = AplicacionForm(request.POST)
        if form.is_valid():
            try:
                nueva_app = form.save()
                logger.info(f"Aplicación '{nueva_app.nombre_aplicacion}' registrada con éxito.")
                messages.success(request, f'¡La aplicación "{nueva_app.nombre_aplicacion}" ha sido registrada con éxito!')
                return redirect('gestion:aplicaciones')
            except Exception as e:
                logger.error(f"Error al guardar aplicación: {e}", exc_info=True)
                messages.error(request, f'Error al guardar: {e}')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = AplicacionForm()

    context = {
        'form': form,
        'todos_los_bloques': Bloque.objects.all().order_by('desc_bloque'),
        'todas_las_criticidades': Criticidad.objects.all().order_by('desc_criticidad'),
        'todos_los_estados': Estado.objects.filter(uso_estado=Estado.UsoChoices.APLICACION).order_by('desc_estado'),
    }
    return render(request, 'gestion/registrar_aplicacion.html', context)


@login_required
@no_cache
def carga_masiva_view(request):
    """
    Gestiona la carga y procesamiento masivo de aplicaciones desde un archivo JSON.
    """
    logger.info(
        f"El usuario '{request.user}' está viendo el formulario de carga masiva.")

    # CORRECCIÓN 4: La función auxiliar se define UNA VEZ fuera del bucle para mayor eficiencia.
    def get_clean_value(data_dict, key, transform=None):
        value = data_dict.get(key)
        if value is None:
            return ''
        clean_value = str(value).strip()
        if transform == 'lower':
            return clean_value.lower()
        return clean_value

    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' ha iniciado una carga masiva de aplicaciones.")
        json_file = request.FILES.get('json_file')
        context = {}

        if not json_file or not json_file.name.endswith('.json'):
            messages.error(
                request, 'Por favor, seleccione un archivo JSON válido.')
            return render(request, 'gestion/carga_masiva_aplicativo.html')

        try:
            # --- 2. Lectura del Archivo ---
            all_rows = json.load(json_file)
            total_records_in_file = len(all_rows)
            logger.info(
                f"Se leyeron {total_records_in_file} objetos del archivo JSON.")

            # --- 3. Pre-validación de ID de Aplicación duplicados en el archivo ---
            logger.info(
                "Iniciando pre-validación de 'id_aplicacion' duplicados...")
            seen_ids, duplicates_found = set(), []
            for line, row in enumerate(all_rows, 1):
                app_id = get_clean_value(row, 'id_aplicacion')
                if app_id:
                    if app_id in seen_ids:
                        duplicates_found.append({'line': line, 'id': app_id})
                    else:
                        seen_ids.add(app_id)

            if duplicates_found:
                error_msg = "El archivo contiene 'id_aplicacion' duplicados."
                messages.error(request, error_msg + " Revisa los detalles.")
                context['duplicates'] = duplicates_found
                return render(request, 'gestion/carga_masiva_aplicativo.html', context)
            logger.info(
                "Pre-validación completada. No se encontraron IDs duplicados.")

            # --- 4. Procesamiento de Filas ---
            criticidad_map = {'alta': 'critica', 'crítica': 'critica', 'media': 'no critica',
                              'no critica': 'no critica', 'baja': 'sin criticidad', 'no crítica': 'no critica'}
            estado_map = {'dev': 'Construccion', 'en construcción': 'Construccion', 'prod': 'Produccion',
                          'en producción': 'Produccion', 'en revisión': 'Pendiente', 'desuso': 'Deshuso'}
            bloque_map = {'b1': 'BLOQUE 1', 'b2': 'BLOQUE 2',
                          'b3': 'BLOQUE 3', 'b4': 'BLOQUE 4', 'ninguno': 'Sin bloque'}

            success_count, failed_rows, skipped_count, modified_rows = 0, [], 0, []

            for line_number, row in enumerate(all_rows, 1):
                obj, created, cod_app_final = None, False, None
                try:
                    id_aplicacion_str = get_clean_value(row, 'id_aplicacion')
                    if not id_aplicacion_str:
                        raise ValueError(
                            "La clave 'id_aplicacion' es obligatoria.")

                    id_aplicacion_pk = int(id_aplicacion_str)
                    cod_aplicacion = get_clean_value(row, 'id_modulo')
                    nombre_aplicacion = get_clean_value(row, 'nombre_app')
                    cod_app_final = cod_aplicacion  # Guardamos el código que se usará para el log

                    if not cod_aplicacion or not nombre_aplicacion:
                        raise ValueError(
                            "'id_modulo' y 'nombre_app' son obligatorios.")

                    # CORRECCIÓN 2: Se añade el bloque que busca los objetos relacionados
                    bloque_str = bloque_map.get(get_clean_value(
                        row, 'bloque', 'lower'), get_clean_value(row, 'bloque'))
                    criticidad_str = criticidad_map.get(get_clean_value(
                        row, 'criticidad', 'lower'), get_clean_value(row, 'criticidad'))
                    estado_str = estado_map.get(get_clean_value(
                        row, 'estado', 'lower'), get_clean_value(row, 'estado'))

                    bloque_obj = Bloque.objects.get(
                        desc_bloque__iexact=bloque_str) if bloque_str else None
                    criticidad_obj = Criticidad.objects.get(
                        desc_criticidad__iexact=criticidad_str) if criticidad_str else None
                    estado_obj = Estado.objects.get(
                        desc_estado__iexact=estado_str) if estado_str else None

                    defaults = {
                        'cod_aplicacion': cod_aplicacion, 'nombre_aplicacion': nombre_aplicacion,
                        'bloque': bloque_obj, 'criticidad': criticidad_obj, 'estado': estado_obj,
                        'desc_aplicacion': get_clean_value(row, 'descripcion')
                    }

                    try:
                        obj, created = Aplicacion.objects.get_or_create(
                            id=id_aplicacion_pk, defaults=defaults)
                    except db_utils.IntegrityError:
                        modified_cod = f"{cod_aplicacion}_ID_{id_aplicacion_pk}"
                        cod_app_final = modified_cod  # Actualizamos el código para el log
                        defaults['cod_aplicacion'] = modified_cod

                        logger.warning(
                            f"Línea {line_number}: 'cod_aplicacion' duplicado ('{cod_aplicacion}'). Modificado a '{modified_cod}'.")
                        obj, created = Aplicacion.objects.get_or_create(
                            id=id_aplicacion_pk, defaults=defaults)

                        if created:
                            modified_rows.append({
                                'line': line_number, 'id': id_aplicacion_pk,
                                'original_cod': cod_aplicacion, 'modified_cod': modified_cod,
                                'nombre_app': nombre_aplicacion
                            })

                except Exception as e:
                    failed_rows.append(
                        {'line': line_number, 'row_data': json.dumps(row), 'error': str(e)})
                    logger.error(
                        f"Error en línea {line_number}: {e}", exc_info=True)

                # CORRECCIÓN 3: El conteo y el log se hacen una sola vez por registro, al final del try/except
                else:
                    if created:
                        success_count += 1
                        logger.info(
                            f"Línea {line_number}: APLICACIÓN CREADA (ID: {id_aplicacion_pk}, Código: '{cod_app_final}').")
                    elif obj:  # Si no fue creado, pero existe el objeto, se omite
                        skipped_count += 1
                        logger.info(
                            f"Línea {line_number}: APLICACIÓN OMITIDA (ID: {id_aplicacion_pk} ya existe).")

            # --- 5. Generación de Resumen y Respuesta ---
            if success_count > 0:
                messages.success(
                    request, f'¡Carga completada! Se crearon {success_count} aplicaciones.')
            if modified_rows:
                messages.warning(
                    request, f"Se modificaron {len(modified_rows)} códigos duplicados. Revise los detalles.")
            if skipped_count > 0:
                messages.info(
                    request, f'Se omitieron {skipped_count} aplicaciones que ya existían.')
            if failed_rows:
                messages.error(
                    request, f'Fallaron {len(failed_rows)} registros. Revise los detalles.')

            # Registro de estadísticas en el log del sistema
            logger.info(
                f"Resumen Carga Masiva (Usuario: {request.user}) - "
                f"Total Leídos: {total_records_in_file} | "
                f"Creados: {success_count} | "
                f"Omitidos (Existentes): {skipped_count} | "
                f"Modificados (Duplicados): {len(modified_rows)} | "
                f"Fallidos: {len(failed_rows)}"
            )

            # CORRECCIÓN 5: Se añade modified_rows y la estadística al contexto
            context = {
                'failed_rows': failed_rows,
                'modified_rows': modified_rows,
                'stats': {
                    'total': total_records_in_file, 'skipped': skipped_count,
                    'success': success_count, 'failed': len(failed_rows),
                    'modified': len(modified_rows)
                }
            }
            return render(request, 'gestion/carga_masiva_aplicativo.html', context)

        except Exception as e:
            logger.critical(
                f"Error CRÍTICO en carga masiva por '{request.user}': {e}", exc_info=True)
            messages.error(
                request, f"Ocurrió un error general e inesperado: {e}")
            return render(request, 'gestion/carga_masiva_aplicativo.html')

    return render(request, 'gestion/carga_masiva_aplicativo.html')


@login_required
@no_cache
def eliminar_aplicacion_view(request, pk):
    """
    Gestiona la eliminación de una aplicación específica.

    Esta vista está protegida para aceptar únicamente peticiones POST,
    como medida de seguridad para prevenir eliminaciones accidentales
    a través de enlaces (peticiones GET).

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        pk (int): La clave primaria (ID) de la aplicación a eliminar.

    Returns:
        HttpResponse: Siempre redirige a la vista 'gestion:aplicaciones'
                      después de la operación.
    """
    # Se valida que la petición sea POST para proceder con la eliminación.
    if request.method == 'POST':
        logger.info(
            f"El usuario '{request.user}' ha iniciado un intento de eliminación para la aplicación con ID: {pk}.")
        try:
            # Se busca la aplicación por su clave primaria.
            aplicacion_a_eliminar = Aplicacion.objects.get(pk=pk)
            nombre_app = aplicacion_a_eliminar.nombre_aplicacion

            # Se elimina el objeto de la base de datos.
            aplicacion_a_eliminar.delete()

            # Se registra la eliminación como una advertencia (WARNING) para que sea
            # fácil de localizar en los logs, ya que es una acción destructiva.
            logger.warning(
                f"ACCIÓN CRÍTICA: El usuario '{request.user}' ha ELIMINADO la aplicación '{nombre_app}' (ID: {pk})."
            )
            messages.success(
                request, f'La aplicación "{nombre_app}" ha sido eliminada correctamente.')

        except Aplicacion.DoesNotExist:
            # Este error ocurre si se intenta eliminar una aplicación que ya no existe.
            logger.warning(
                f"Intento de eliminación fallido: La aplicación con ID {pk} no existe. Solicitado por '{request.user}'."
            )
            messages.error(
                request, 'La aplicación que intentas eliminar no existe.')

        except Exception as e:
            # Captura cualquier otro error inesperado durante la eliminación.
            logger.error(
                f"Error crítico al eliminar la aplicación ID {pk} por el usuario '{request.user}'. Error: {e}",
                exc_info=True
            )
            messages.error(
                request, f'Ocurrió un error al eliminar la aplicación: {e}')

    # Si la petición no es POST, o después de la operación, se redirige.
    return redirect('gestion:aplicaciones')


@login_required
@no_cache
@login_required
@no_cache
def editar_aplicacion_view(request, pk):
    """
    Gestiona la edición de una aplicación existente usando Django Forms.
    """
    aplicacion = get_object_or_404(Aplicacion, pk=pk) # get_object_or_404 should be imported if not already

    if request.method == 'POST':
        form = AplicacionForm(request.POST, instance=aplicacion)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f'¡La aplicación "{aplicacion.nombre_aplicacion}" ha sido actualizada correctamente.')
                return redirect('gestion:aplicaciones')
            except Exception as e:
                logger.error(f"Error al actualizar aplicación: {e}", exc_info=True)
                messages.error(request, f'Error al actualizar: {e}')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = AplicacionForm(instance=aplicacion)

    context = {
        'form': form,
        'aplicacion': aplicacion,
        'todos_los_bloques': Bloque.objects.all().order_by('desc_bloque'),
        'todas_las_criticidades': Criticidad.objects.all().order_by('desc_criticidad'),
        'todos_los_estados': Estado.objects.filter(uso_estado=Estado.UsoChoices.APLICACION).order_by('desc_estado'),
    }
    return render(request, 'gestion/registrar_aplicacion.html', context)
    return render(request, 'gestion/registrar_aplicacion.html', context)


@login_required
@no_cache
def exportar_aplicaciones_csv(request):
    """
    Genera y descarga un archivo CSV con el listado de aplicaciones filtrado.
    Recibe los mismos parámetros GET que la vista de listado para aplicar filtros.
    """
    # --- 1. Queryset Base ---
    aplicaciones_qs = Aplicacion.objects.select_related(
        'bloque', 'criticidad', 'estado').all()

    # --- 2. Procesamiento de Filtros (Copia de la lógica de aplicaciones_view) ---
    filtro_nombre = request.GET.get('nombre_app')
    filtro_codigo = request.GET.get('codigo_app')
    filtro_bloque_id = request.GET.get('bloque')
    filtro_criticidad_id = request.GET.get('criticidad')
    filtro_estado_id = request.GET.get('estado')

    if filtro_nombre:
        aplicaciones_qs = aplicaciones_qs.filter(
            nombre_aplicacion__icontains=filtro_nombre)

    if filtro_codigo:
        aplicaciones_qs = aplicaciones_qs.filter(
            cod_aplicacion__icontains=filtro_codigo)

    if filtro_bloque_id and filtro_bloque_id.isdigit():
        aplicaciones_qs = aplicaciones_qs.filter(bloque_id=filtro_bloque_id)

    if filtro_criticidad_id and filtro_criticidad_id.isdigit():
        aplicaciones_qs = aplicaciones_qs.filter(
            criticidad_id=filtro_criticidad_id)

    if filtro_estado_id and filtro_estado_id.isdigit():
        aplicaciones_qs = aplicaciones_qs.filter(estado_id=filtro_estado_id)

    # --- 3. Generación del CSV ---
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="aplicaciones.csv"'
    response.write(u'\ufeff'.encode('utf8')) # BOM para Excel

    writer = csv.writer(response, delimiter=';') # Delimitador ; para Excel en español
    writer.writerow(['ID', 'Código', 'Nombre', 'Bloque', 'Criticidad', 'Estado', 'Descripción'])

    for app in aplicaciones_qs:
        writer.writerow([
            app.id,
            app.cod_aplicacion,
            app.nombre_aplicacion,
            app.bloque.desc_bloque if app.bloque else '',
            app.criticidad.desc_criticidad if app.criticidad else '',
            app.estado.desc_estado if app.estado else '',
            app.desc_aplicacion
        ])

    return response
