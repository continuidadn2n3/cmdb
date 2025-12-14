# gestion/views/cod_cierre.py

import json
import csv
import datetime
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .utils import no_cache, logger
from ..models import CodigoCierre, Aplicacion
from ..forms import CodigoCierreForm

# --- Vistas del CRUD para Códigos de Cierre ---


@login_required
@no_cache
def codigos_cierre_view(request):
    """
    Muestra la lista de códigos de cierre con opción de filtrado.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.

    Returns:
        HttpResponse: Renderiza la plantilla 'gestion/cod_cierre.html' con el contexto.

    Context:
        'lista_de_codigos' (QuerySet): Códigos de cierre filtrados.
        'total_registros' (int): Conteo total de códigos en la BD.
        'todas_las_aplicaciones' (QuerySet): Lista de aplicaciones para el filtro.
    """
    logger.info(
        f"Usuario '{request.user}' está viendo la lista de códigos de cierre.")
    codigos_qs = CodigoCierre.objects.select_related('aplicacion').all()

    # Procesamiento de filtros
    filtro_codigo = request.GET.get('codigo_cierre')
    filtro_app_id = request.GET.get('aplicacion')
    filtros_aplicados = []

    if filtro_codigo:
        codigos_qs = codigos_qs.filter(cod_cierre__icontains=filtro_codigo)
        filtros_aplicados.append(f"código='{filtro_codigo}'")
    if filtro_app_id and filtro_app_id.isdigit():
        codigos_qs = codigos_qs.filter(aplicacion_id=filtro_app_id)
        filtros_aplicados.append(f"aplicacion_id='{filtro_app_id}'")

    if filtros_aplicados:
        logger.info(
            f"Búsqueda de códigos con filtros: {', '.join(filtros_aplicados)}.")

    context = {
        'lista_de_codigos': codigos_qs,
        'total_registros': CodigoCierre.objects.count(),
        'todas_las_aplicaciones': Aplicacion.objects.all().order_by('nombre_aplicacion'),
    }
    return render(request, 'gestion/cod_cierre.html', context)


@login_required
@no_cache
def exportar_codigos_cierre_csv(request):
    """
    Genera y descarga un archivo CSV con el listado de códigos de cierre,
    respetando los filtros aplicados en la vista.
    """
    logger.info(f"Usuario '{request.user}' solicitó exportación CSV de Códigos de Cierre.")
    
    # Base QuerySet
    codigos_qs = CodigoCierre.objects.select_related('aplicacion').all()

    # Aplicar mismos filtros que en la vista principal
    filtro_codigo = request.GET.get('codigo_cierre')
    filtro_app_id = request.GET.get('aplicacion')

    if filtro_codigo:
        codigos_qs = codigos_qs.filter(cod_cierre__icontains=filtro_codigo)
    if filtro_app_id and filtro_app_id.isdigit():
        codigos_qs = codigos_qs.filter(aplicacion_id=filtro_app_id)

    # Crear respuesta HTTP con tipo CSV
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    response['Content-Disposition'] = f'attachment; filename="codigos_cierre_{timestamp}.csv"'

    # Crear escritor CSV
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['ID', 'Código Cierre', 'Aplicación', 'Descripción', 'Causa Cierre'])

    for codigo in codigos_qs:
        writer.writerow([
            codigo.id,
            codigo.cod_cierre,
            codigo.aplicacion.nombre_aplicacion if codigo.aplicacion else 'N/A',
            codigo.desc_cod_cierre,
            codigo.causa_cierre
        ])

    return response



@login_required
@no_cache
@login_required
@no_cache
def registrar_cod_cierre_view(request):
    """
    Gestiona la creación de un nuevo código de cierre usando Django Forms.
    """
    if request.method == 'POST':
        logger.info(f"Usuario '{request.user}' intenta registrar un nuevo código de cierre.")
        form = CodigoCierreForm(request.POST)
        if form.is_valid():
            try:
                # Verificación manual de duplicados (opcional, pero mantenemos la lógica original)
                cod_cierre = form.cleaned_data['cod_cierre']
                aplicacion = form.cleaned_data['aplicacion']
                if CodigoCierre.objects.filter(cod_cierre=cod_cierre, aplicacion=aplicacion).exists():
                    messages.error(request, f"Ya existe un código de cierre '{cod_cierre}' para la aplicación '{aplicacion.nombre_aplicacion}'.")
                else:
                    nuevo_codigo = form.save()
                    logger.info(f"Usuario '{request.user}' registró con éxito el código '{nuevo_codigo.cod_cierre}' (ID: {nuevo_codigo.id}).")
                    messages.success(request, f'¡El código de cierre "{nuevo_codigo.cod_cierre}" ha sido registrado con éxito!')
                    return redirect('gestion:codigos_cierre')
            except Exception as e:
                logger.error(f"Error al registrar código de cierre: {e}", exc_info=True)
                messages.error(request, f'Error al registrar: {e}')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = CodigoCierreForm()

    context = {
        'form': form,
        'todas_las_aplicaciones': Aplicacion.objects.all().order_by('nombre_aplicacion')
    }
    return render(request, 'gestion/registrar_cod_cierre.html', context)


@login_required
@no_cache
@login_required
@no_cache
def editar_cod_cierre_view(request, pk):
    """
    Gestiona la edición de un código de cierre existente usando Django Forms.
    """
    codigo_a_editar = get_object_or_404(CodigoCierre, pk=pk)

    if request.method == 'POST':
        logger.info(f"Usuario '{request.user}' intenta actualizar el código de cierre ID: {pk}.")
        form = CodigoCierreForm(request.POST, instance=codigo_a_editar)
        if form.is_valid():
            try:
                # Verificación manual de duplicados excluyendo el actual
                cod_cierre = form.cleaned_data['cod_cierre']
                aplicacion = form.cleaned_data['aplicacion']
                if CodigoCierre.objects.filter(cod_cierre=cod_cierre, aplicacion=aplicacion).exclude(pk=pk).exists():
                    messages.error(request, f"Ya existe otro código de cierre '{cod_cierre}' para la aplicación '{aplicacion.nombre_aplicacion}'.")
                else:
                    form.save()
                    logger.info(f"Usuario '{request.user}' actualizó con éxito el código '{codigo_a_editar.cod_cierre}' (ID: {pk}).")
                    messages.success(request, f'El código de cierre "{codigo_a_editar.cod_cierre}" ha sido actualizado.')
                    return redirect('gestion:codigos_cierre')
            except Exception as e:
                logger.error(f"Error al actualizar código de cierre: {e}", exc_info=True)
                messages.error(request, f'Error al actualizar: {e}')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = CodigoCierreForm(instance=codigo_a_editar)

    context = {
        'form': form,
        'codigo_cierre': codigo_a_editar,
        'todas_las_aplicaciones': Aplicacion.objects.all().order_by('nombre_aplicacion')
    }
    return render(request, 'gestion/registrar_cod_cierre.html', context)


@login_required
@no_cache
def eliminar_cod_cierre_view(request, pk):
    """
    Elimina un código de cierre específico. Solo permite peticiones POST.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        pk (int): La clave primaria del código a eliminar.

    Returns:
        HttpResponse: Siempre redirige a la lista de códigos de cierre.
    """
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta eliminar el código de cierre ID: {pk}.")
        try:
            codigo_a_eliminar = CodigoCierre.objects.get(pk=pk)
            nombre_codigo = codigo_a_eliminar.cod_cierre
            codigo_a_eliminar.delete()
            logger.warning(
                f"ACCIÓN CRÍTICA: El usuario '{request.user}' ha ELIMINADO el código '{nombre_codigo}' (ID: {pk}).")
            messages.success(
                request, f'El código de cierre "{nombre_codigo}" ha sido eliminado.')
        except CodigoCierre.DoesNotExist:
            logger.warning(
                f"Intento de eliminación fallido: código inexistente (ID: {pk}). Usuario: '{request.user}'.")
            messages.error(
                request, 'El código de cierre que intentas eliminar no existe.')
        except Exception as e:
            logger.error(
                f"Error al eliminar código de cierre ID {pk} por '{request.user}': {e}", exc_info=True)
            messages.error(request, f'Ocurrió un error al eliminar: {e}')

    return redirect('gestion:codigos_cierre')


# --- Vista de Carga Masiva ---

@login_required
@no_cache
def carga_masiva_cod_cierre_view(request):
    """
    Gestiona la carga masiva de códigos de cierre desde un archivo JSON.
    """
    logger.info(
        f"Usuario '{request.user}' está viendo la carga masiva de Códigos de Cierre.")

    def get_clean_value(data_dict, key):
        value = data_dict.get(key)
        return str(value).strip() if value is not None else ''

    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' inició una carga masiva de Códigos de Cierre.")
        json_file = request.FILES.get('json_file')
        context = {}

        if not json_file or not json_file.name.endswith('.json'):
            messages.error(
                request, 'Por favor, seleccione un archivo JSON válido.')
            return render(request, 'gestion/carga_masiva_cod_cierre.html')

        try:
            all_rows = json.load(json_file)
            total_records_in_file = len(all_rows)
            logger.info(
                f"Se leyeron {total_records_in_file} objetos del archivo JSON.")

            # Pre-validación de 'idCodCierre' duplicados en el archivo
            seen_ids, duplicates_found = set(), []
            for line, row in enumerate(all_rows, 1):
                pk_id = get_clean_value(row, 'idCodCierre')
                if pk_id:
                    if pk_id in seen_ids:
                        duplicates_found.append({'line': line, 'id': pk_id})
                    else:
                        seen_ids.add(pk_id)

            if duplicates_found:
                messages.error(
                    request, "El archivo contiene 'idCodCierre' duplicados. Revisa los detalles.")
                context['duplicates'] = duplicates_found
                return render(request, 'gestion/carga_masiva_cod_cierre.html', context)

            # Procesamiento de filas
            created_count, updated_count, failed_rows = 0, 0, []
            app_cache = {str(app.id): app for app in Aplicacion.objects.all()}

            for line_number, row in enumerate(all_rows, 1):
                try:
                    cod_cierre = get_clean_value(row, 'cod_cierre')
                    id_aplicacion = get_clean_value(row, 'id_aplicacion')

                    if not cod_cierre or not id_aplicacion:
                        raise ValueError(
                            "Las claves 'cod_cierre' y 'id_aplicacion' son obligatorias.")

                    aplicacion_obj = app_cache.get(id_aplicacion)
                    if not aplicacion_obj:
                        error_msg = f"La Aplicación con ID '{id_aplicacion}' no existe en la base de datos."
                        logger.warning(f"Línea {line_number}: {error_msg} (Registro omitido).")
                        failed_rows.append(
                            {'line': line_number, 'row_data': json.dumps(row), 'error': error_msg})
                        continue

                    obj, created = CodigoCierre.objects.update_or_create(
                        cod_cierre=cod_cierre,
                        aplicacion=aplicacion_obj,
                        defaults={
                            'desc_cod_cierre': get_clean_value(row, 'descripcion_cierre'),
                            'causa_cierre': get_clean_value(row, 'causa_cierre')
                        }
                    )

                    if created:
                        created_count += 1
                        logger.info(
                            f"Línea {line_number}: CÓDIGO CIERRE CREADO (ID: {obj.id}, Código: '{cod_cierre}').")
                    else:
                        updated_count += 1
                        logger.info(
                            f"Línea {line_number}: CÓDIGO CIERRE ACTUALIZADO (ID: {obj.id}, Código: '{cod_cierre}').")

                except Exception as e:
                    failed_rows.append(
                        {'line': line_number, 'row_data': json.dumps(row), 'error': str(e)})
                    logger.error(
                        f"Error procesando línea {line_number}: {e}", exc_info=True)

            # Resumen y mensajes
            if created_count > 0:
                messages.success(
                    request, f'¡Carga completada! Se crearon {created_count} nuevos códigos.')
            if updated_count > 0:
                messages.info(
                    request, f'Se actualizaron {updated_count} códigos que ya existían.')
            if failed_rows:
                messages.error(
                    request, f'Fallaron {len(failed_rows)} registros. Revisa los detalles.')

            # Preparar string con líneas fallidas
            failed_lines_str = ""
            if failed_rows:
                failed_lines = [str(item['line']) for item in failed_rows]
                failed_lines_str = f" (Líneas: {', '.join(failed_lines)})"

            # Registro de estadísticas en el log del sistema
            logger.info(
                f"Resumen Carga Masiva Códigos Cierre (Usuario: {request.user}) - "
                f"Total Leídos: {total_records_in_file} | "
                f"Creados: {created_count} | "
                f"Actualizados: {updated_count} | "
                f"Fallidos: {len(failed_rows)}{failed_lines_str}"
            )

            context = {
                'failed_rows': failed_rows,
                'stats': {
                    'total': total_records_in_file,
                    'success': created_count,
                    'updated': updated_count,
                    'failed': len(failed_rows)
                }
            }
            return render(request, 'gestion/carga_masiva_cod_cierre.html', context)

        except Exception as e:
            logger.critical(
                f"Error CRÍTICO en carga masiva de códigos por '{request.user}': {e}", exc_info=True)
            messages.error(
                request, f"Ocurrió un error general e inesperado: {e}")
            return render(request, 'gestion/carga_masiva_cod_cierre.html')

    return render(request, 'gestion/carga_masiva_cod_cierre.html')

# --- Vista para AJAX ---


def obtener_ultimos_codigos_cierre(request, aplicacion_id):
    """
    Endpoint API para ser llamado vía AJAX.

    Devuelve los 5 códigos de cierre más recientes para una aplicación específica,
    en formato JSON. Usado para asistir en la entrada de datos en otros formularios.

    Args:
        request (HttpRequest): El objeto de solicitud HTTP.
        aplicacion_id (int): El ID de la aplicación para la cual buscar códigos.

    Returns:
        JsonResponse: Un objeto JSON con una lista de códigos o un mensaje de error.
    """

    logger.info(
        f"Petición AJAX recibida para obtener códigos de la app ID: {aplicacion_id}.")
    try:
        codigos = CodigoCierre.objects.filter(
            aplicacion_id=aplicacion_id).order_by('-id')[:5]
        data = list(codigos.values('cod_cierre', 'desc_cod_cierre'))
        return JsonResponse({'codigos': data})
    except Exception as e:
        logger.error(
            f"Error en AJAX 'obtener_ultimos_codigos_cierre' para app_id {aplicacion_id}: {e}", exc_info=True)
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)
