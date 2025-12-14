from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import ProtectedError
from ..models import Usuario, Estado, GrupoResolutor, ReglaSLA, DiaFeriado, HorarioLaboral
from ..forms import UsuarioForm, ReglaSLAForm, HorarioLaboralForm, EstadoForm, GrupoResolutorForm, DiaFeriadoForm
from .utils import logger


def mantenedores_main(request):
    """Página principal que muestra las tarjetas de los diferentes mantenedores."""
    logger.info(
        f"Usuario '{request.user}' accedió al menú principal de mantenedores.")
    return render(request, 'gestion/mantenedores/mantenedores_main.html')

# === Vistas para Usuarios ===


def listar_usuarios(request):
    """Muestra la lista de todos los usuarios."""
    logger.info(f"Usuario '{request.user}' está viendo la lista de usuarios.")
    registros = Usuario.objects.all().order_by('usuario')
    context = {
        'registros': registros,
    }
    return render(request, 'gestion/mantenedores/listar_usuarios.html', context)


def registrar_usuario(request):
    """Maneja la creación de un nuevo usuario."""
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta registrar un nuevo usuario.")
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            logger.info(
                f"Usuario '{request.user}' registró con éxito al usuario '{usuario.usuario}' (ID: {usuario.id}).")
            messages.success(
                request, f"El usuario '{usuario.usuario}' ha sido registrado correctamente.")
            return redirect('gestion:listar_usuarios')
        else:
            logger.warning(
                f"Fallo de validación al registrar usuario por '{request.user}'. Errores: {form.errors.as_json()}")
    else:
        logger.info(
            f"Usuario '{request.user}' accedió al formulario de registro de usuario.")
        form = UsuarioForm()

    context = {
        'form': form,
        'title': 'Agregar Usuario',
        'action_url': reverse_lazy('gestion:registrar_usuario')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_usuario(request, pk):
    """Maneja la edición de un usuario existente."""
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta editar al usuario '{usuario.usuario}' (ID: {pk}).")
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            logger.info(
                f"Usuario '{request.user}' actualizó con éxito al usuario '{usuario.usuario}' (ID: {pk}).")
            messages.success(
                request, f"El usuario '{usuario.usuario}' ha sido actualizado correctamente.")
            return redirect('gestion:listar_usuarios')
        else:
            logger.warning(
                f"Fallo de validación al editar usuario ID {pk} por '{request.user}'. Errores: {form.errors.as_json()}")
    else:
        logger.info(
            f"Usuario '{request.user}' accedió al formulario para editar al usuario '{usuario.usuario}' (ID: {pk}).")
        form = UsuarioForm(instance=usuario)

    context = {
        'form': form,
        'title': 'Editar Usuario',
        'action_url': reverse_lazy('gestion:editar_usuario', kwargs={'pk': usuario.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_usuario(request, pk):
    """Elimina un usuario."""
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta eliminar al usuario '{usuario.usuario}' (ID: {pk}).")
        try:
            nombre_usuario = usuario.usuario
            usuario.delete()
            logger.warning(
                f"ACCIÓN CRÍTICA: Usuario '{request.user}' ha ELIMINADO al usuario '{nombre_usuario}' (ID: {pk}).")
            messages.success(
                request, f"El usuario '{nombre_usuario}' ha sido eliminado.")
        except ProtectedError:
            logger.error(
                f"Intento de eliminación fallido por '{request.user}' para el usuario ID {pk} debido a ProtectedError.")
            messages.error(
                request, f"No se puede eliminar al usuario '{usuario.usuario}' porque está asignado a incidencias.")
    return redirect('gestion:listar_usuarios')


# === Vistas para Estados (Placeholder) ===
def listar_estados(request):
    """Muestra la lista de todos los estados."""
    logger.info(f"Usuario '{request.user}' está viendo la lista de estados.")
    registros = Estado.objects.all().order_by('desc_estado')
    context = {
        'registros': registros
    }
    return render(request, 'gestion/mantenedores/listar_estados.html', context)


def registrar_estado(request):
    """Maneja la creación de un nuevo estado."""
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta registrar un nuevo estado.")
        form = EstadoForm(request.POST)
        if form.is_valid():
            estado = form.save()
            logger.info(
                f"Usuario '{request.user}' registró con éxito el estado '{estado.desc_estado}' (ID: {estado.id}).")
            messages.success(
                request, "El estado ha sido registrado correctamente.")
            return redirect('gestion:listar_estados')
        else:
            logger.warning(
                f"Fallo de validación al registrar estado por '{request.user}'. Errores: {form.errors.as_json()}")
    else:
        logger.info(
            f"Usuario '{request.user}' accedió al formulario de registro de estado.")
        form = EstadoForm()

    context = {
        'form': form,
        'title': 'Agregar Estado',
        'action_url': reverse_lazy('gestion:registrar_estado')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_estado(request, pk):
    """Maneja la edición de un estado existente."""
    estado = get_object_or_404(Estado, pk=pk)
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta editar el estado '{estado.desc_estado}' (ID: {pk}).")
        form = EstadoForm(request.POST, instance=estado)
        if form.is_valid():
            form.save()
            logger.info(
                f"Usuario '{request.user}' actualizó con éxito el estado '{estado.desc_estado}' (ID: {pk}).")
            messages.success(
                request, "El estado ha sido actualizado correctamente.")
            return redirect('gestion:listar_estados')
        else:
            logger.warning(
                f"Fallo de validación al editar estado ID {pk} por '{request.user}'. Errores: {form.errors.as_json()}")
    else:
        logger.info(
            f"Usuario '{request.user}' accedió al formulario para editar el estado '{estado.desc_estado}' (ID: {pk}).")
        form = EstadoForm(instance=estado)

    context = {
        'form': form,
        'title': 'Editar Estado',
        'action_url': reverse_lazy('gestion:editar_estado', kwargs={'pk': estado.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_estado(request, pk):
    """Elimina un estado, con protección para evitar borrar registros en uso."""
    estado = get_object_or_404(Estado, pk=pk)
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta eliminar el estado '{estado.desc_estado}' (ID: {pk}).")
        try:
            estado_desc = estado.desc_estado
            estado.delete()
            logger.warning(
                f"ACCIÓN CRÍTICA: Usuario '{request.user}' ha ELIMINADO el estado '{estado_desc}' (ID: {pk}).")
            messages.success(
                request, f"El estado '{estado_desc}' ha sido eliminado correctamente.")
        except ProtectedError:
            messages.error(
                request, f"No se puede eliminar el estado '{estado.desc_estado}' porque está en uso (ej. en Aplicaciones o Incidencias).")
            logger.error(
                f"Intento de eliminación fallido por '{request.user}' para el estado ID {pk} debido a ProtectedError.")
    return redirect('gestion:listar_estados')

# === Vistas para Grupos Resolutores (Placeholder) ===


def listar_grupos(request):
    """Muestra la lista de todos los grupos resolutores."""
    logger.info(
        f"Usuario '{request.user}' está viendo la lista de grupos resolutores.")
    registros = GrupoResolutor.objects.all().order_by('desc_grupo_resol')
    context = {
        'registros': registros
    }
    return render(request, 'gestion/mantenedores/listar_grupos.html', context)


def registrar_grupo(request):
    """Maneja la creación de un nuevo grupo resolutor."""
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta registrar un nuevo grupo resolutor.")
        form = GrupoResolutorForm(request.POST)
        if form.is_valid():
            grupo = form.save()
            logger.info(
                f"Usuario '{request.user}' registró con éxito el grupo '{grupo.desc_grupo_resol}' (ID: {grupo.id}).")
            messages.success(
                request, "El grupo resolutor ha sido registrado correctamente.")
            return redirect('gestion:listar_grupos')
        else:
            logger.warning(
                f"Fallo de validación al registrar grupo por '{request.user}'. Errores: {form.errors.as_json()}")
    else:
        logger.info(
            f"Usuario '{request.user}' accedió al formulario de registro de grupo resolutor.")
        form = GrupoResolutorForm()

    context = {
        'form': form,
        'title': 'Agregar Grupo Resolutor',
        'action_url': reverse_lazy('gestion:registrar_grupo')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_grupo(request, pk):
    """Maneja la edición de un grupo resolutor existente."""
    grupo = get_object_or_404(GrupoResolutor, pk=pk)
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta editar el grupo '{grupo.desc_grupo_resol}' (ID: {pk}).")
        form = GrupoResolutorForm(request.POST, instance=grupo)
        if form.is_valid():
            form.save()
            logger.info(
                f"Usuario '{request.user}' actualizó con éxito el grupo '{grupo.desc_grupo_resol}' (ID: {pk}).")
            messages.success(
                request, "El grupo resolutor ha sido actualizado correctamente.")
            return redirect('gestion:listar_grupos')
        else:
            logger.warning(
                f"Fallo de validación al editar grupo ID {pk} por '{request.user}'. Errores: {form.errors.as_json()}")
    else:
        logger.info(
            f"Usuario '{request.user}' accedió al formulario para editar el grupo '{grupo.desc_grupo_resol}' (ID: {pk}).")
        form = GrupoResolutorForm(instance=grupo)

    context = {
        'form': form,
        'title': 'Editar Grupo Resolutor',
        'action_url': reverse_lazy('gestion:editar_grupo', kwargs={'pk': grupo.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_grupo(request, pk):
    """Elimina un grupo resolutor."""
    grupo = get_object_or_404(GrupoResolutor, pk=pk)
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta eliminar el grupo '{grupo.desc_grupo_resol}' (ID: {pk}).")
        try:
            grupo_desc = grupo.desc_grupo_resol
            grupo.delete()
            logger.warning(
                f"ACCIÓN CRÍTICA: Usuario '{request.user}' ha ELIMINADO el grupo '{grupo_desc}' (ID: {pk}).")
            messages.success(
                request, f"El grupo resolutor '{grupo_desc}' ha sido eliminado correctamente.")
        except ProtectedError:
            logger.error(
                f"Intento de eliminación fallido por '{request.user}' para el grupo ID {pk} debido a ProtectedError.")
            messages.error(
                request, f"No se puede eliminar el grupo '{grupo.desc_grupo_resol}' porque está en uso.")
    return redirect('gestion:listar_grupos')

# ... y así sucesivamente para los otros mantenedores ...


def listar_reglas_sla(request):
    """Muestra la lista de todas las reglas de SLA."""
    # Usamos select_related para optimizar la consulta y evitar N+1 queries
    logger.info(
        f"Usuario '{request.user}' está viendo la lista de reglas de SLA.")
    registros = ReglaSLA.objects.select_related(
        'severidad', 'criticidad_aplicacion').all()
    context = {
        'registros': registros
    }
    return render(request, 'gestion/mantenedores/listar_reglas_sla.html', context)


def registrar_regla_sla(request):
    """Maneja la creación de una nueva regla de SLA."""
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta registrar una nueva regla de SLA.")
        form = ReglaSLAForm(request.POST)
        if form.is_valid():
            regla = form.save()
            logger.info(
                f"Usuario '{request.user}' registró con éxito la regla de SLA '{regla}' (ID: {regla.id}).")
            messages.success(
                request, "La regla de SLA ha sido registrada correctamente.")
            return redirect('gestion:listar_reglas_sla')
        else:
            logger.warning(
                f"Fallo de validación al registrar regla SLA por '{request.user}'. Errores: {form.errors.as_json()}")
    else:
        logger.info(
            f"Usuario '{request.user}' accedió al formulario de registro de regla de SLA.")
        form = ReglaSLAForm()

    context = {
        'form': form,
        'title': 'Registrar Regla de SLA',
        'action_url': reverse_lazy('gestion:registrar_regla_sla')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_regla_sla(request, pk):
    """Maneja la edición de una regla de SLA existente."""
    regla = get_object_or_404(ReglaSLA, pk=pk)
    if request.method == 'POST':
        logger.info(
            f"Usuario '{request.user}' intenta editar la regla de SLA '{regla}' (ID: {pk}).")
        form = ReglaSLAForm(request.POST, instance=regla)
        if form.is_valid():
            form.save()
            logger.info(
                f"Usuario '{request.user}' actualizó con éxito la regla de SLA '{regla}' (ID: {pk}).")
            messages.success(
                request, "La regla de SLA ha sido actualizada correctamente.")
            return redirect('gestion:listar_reglas_sla')
        else:
            logger.warning(
                f"Fallo de validación al editar regla SLA ID {pk} por '{request.user}'. Errores: {form.errors.as_json()}")
    else:
        logger.info(
            f"Usuario '{request.user}' accedió al formulario para editar la regla de SLA '{regla}' (ID: {pk}).")
        form = ReglaSLAForm(instance=regla)

    context = {
        'form': form,
        'title': 'Editar Regla de SLA',
        'action_url': reverse_lazy('gestion:editar_regla_sla', kwargs={'pk': regla.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_regla_sla(request, pk):
    """Elimina una regla de SLA."""
    regla = get_object_or_404(ReglaSLA, pk=pk)
    if request.method == 'POST':
        regla_desc = str(regla)
        logger.info(
            f"Usuario '{request.user}' intenta eliminar la regla de SLA '{regla_desc}' (ID: {pk}).")
        regla.delete()
        logger.warning(
            f"ACCIÓN CRÍTICA: Usuario '{request.user}' ha ELIMINADO la regla de SLA '{regla_desc}' (ID: {pk}).")
        messages.success(
            request, f"La regla de SLA para '{regla_desc}' ha sido eliminada.")
    return redirect('gestion:listar_reglas_sla')


def listar_dias_feriados(request):
    """Muestra la lista de todos los días feriados."""
    logger.info(
        f"Usuario '{request.user}' está viendo la lista de días feriados.")
    registros = DiaFeriado.objects.all().order_by('fecha')
    context = {
        'registros': registros
    }
    return render(request, 'gestion/mantenedores/listar_dias_feriados.html', context)


def registrar_dia_feriado(request):
    """Maneja la creación de un nuevo día feriado."""
    if request.method == 'POST':
        form = DiaFeriadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "El día feriado ha sido registrado correctamente.")
            return redirect('gestion:listar_dias_feriados')
    else:
        form = DiaFeriadoForm()

    context = {
        'form': form,
        'title': 'Agregar Día Feriado',
        'action_url': reverse_lazy('gestion:registrar_dia_feriado')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_dia_feriado(request, pk):
    """Maneja la edición de un día feriado existente."""
    feriado = get_object_or_404(DiaFeriado, pk=pk)
    if request.method == 'POST':
        form = DiaFeriadoForm(request.POST, instance=feriado)
        if form.is_valid():
            form.save()
            messages.success(
                request, "El día feriado ha sido actualizado correctamente.")
            return redirect('gestion:listar_dias_feriados')
    else:
        form = DiaFeriadoForm(instance=feriado)

    context = {
        'form': form,
        'title': 'Editar Día Feriado',
        'action_url': reverse_lazy('gestion:editar_dia_feriado', kwargs={'pk': feriado.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_dia_feriado(request, pk):
    """Elimina un día feriado."""
    feriado = get_object_or_404(DiaFeriado, pk=pk)
    if request.method == 'POST':
        feriado_desc = f"{feriado.fecha.strftime('%d-%m-%Y')} - {feriado.descripcion}"
        feriado.delete()
        messages.success(
            request, f"El día feriado '{feriado_desc}' ha sido eliminado correctamente.")
    return redirect('gestion:listar_dias_feriados')


def listar_horarios_laborales(request):
    """
    Muestra la lista de todos los horarios laborales y determina si se pueden
    agregar nuevos (si no existen registros para los 7 días de la semana).
    """
    registros = HorarioLaboral.objects.all()
    se_pueden_agregar_mas = registros.count() < 7
    context = {
        'registros': registros,
        'se_pueden_agregar_mas': se_pueden_agregar_mas,
    }
    return render(request, 'gestion/mantenedores/listar_horarios_laborales.html', context)


def registrar_horario_laboral(request):
    """Maneja la creación de un nuevo horario laboral para un día de la semana faltante."""
    if request.method == 'POST':
        form = HorarioLaboralForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "El nuevo horario laboral ha sido registrado correctamente.")
            return redirect('gestion:listar_horarios_laborales')
    else:
        form = HorarioLaboralForm()

    context = {
        'form': form,
        'title': 'Agregar Horario Laboral',
        'action_url': reverse_lazy('gestion:registrar_horario_laboral')
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def editar_horario_laboral(request, pk):
    """Maneja la edición de un horario laboral existente."""
    horario = get_object_or_404(HorarioLaboral, pk=pk)
    if request.method == 'POST':
        form = HorarioLaboralForm(request.POST, instance=horario)
        if form.is_valid():
            form.save()
            messages.success(
                request, f"El horario para el {horario.get_dia_semana_display()} ha sido actualizado correctamente.")
            return redirect('gestion:listar_horarios_laborales')
    else:
        form = HorarioLaboralForm(instance=horario)

    context = {
        'form': form,
        'title': f'Editar Horario para {horario.get_dia_semana_display()}',
        'action_url': reverse_lazy('gestion:editar_horario_laboral', kwargs={'pk': horario.id})
    }
    return render(request, 'gestion/mantenedores/mantenedor_form.html', context)


def eliminar_horario_laboral(request, pk):
    """Elimina un horario laboral, permitiendo que se pueda volver a crear."""
    horario = get_object_or_404(HorarioLaboral, pk=pk)
    if request.method == 'POST':
        dia_semana_display = horario.get_dia_semana_display()
        horario.delete()
        messages.success(
            request, f"El horario para el {dia_semana_display} ha sido eliminado correctamente.")
    return redirect('gestion:listar_horarios_laborales')
