from django.contrib import admin
from .models import (
    Bloque,
    Cluster,
    Criticidad,
    GrupoResolutor,
    Impacto,
    Estado,
    Interfaz,
    Aplicacion,
    CodigoCierre,
    Incidencia,
    Severidad,
    Usuario,
    ReglaSLA,
    HorarioLaboral,
    DiaFeriado,
)

# Usamos el decorador @admin.register para todos los modelos para mantener la consistencia.
# Para los modelos de catálogo que no necesitan personalización, podemos usar una clase genérica.


@admin.register(Bloque, Cluster, Criticidad, GrupoResolutor, Impacto, Estado, Interfaz, Severidad, Usuario, HorarioLaboral, DiaFeriado)
class CatalogoAdmin(admin.ModelAdmin):
    """
    Registro genérico para modelos de catálogo simples.
    Permite búsquedas en el campo principal si existe.
    """

    def get_search_fields(self, request, obj=None):
        # Intenta añadir un campo de búsqueda por defecto
        try:
            # Busca el primer campo CharField o TextField para usarlo en la búsqueda
            field = next(f for f in self.model._meta.fields if isinstance(
                f, (admin.models.CharField, admin.models.TextField)))
            return (field.name,)
        except StopIteration:
            return ()

# --- Registros Personalizados ---


@admin.register(ReglaSLA)
class ReglaSLAAdmin(admin.ModelAdmin):
    """
    Personaliza la vista de las Reglas de SLA en el panel de administrador.
    """
    list_display = ('severidad', 'criticidad_aplicacion',
                    'tiempo_sla_formato_hhmmss', 'tiempo_sla_en_minutos')
    list_filter = ('severidad', 'criticidad_aplicacion')
    list_select_related = ('severidad', 'criticidad_aplicacion')

    def tiempo_sla_formato_hhmmss(self, obj):
        if not obj.tiempo_sla:
            return "N/A"
        total_seconds = int(obj.tiempo_sla.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    tiempo_sla_formato_hhmmss.short_description = "Tiempo SLA (HH:MM:SS)"

    def tiempo_sla_en_minutos(self, obj):
        return int(obj.tiempo_sla.total_seconds() / 60) if obj.tiempo_sla else 0
    tiempo_sla_en_minutos.short_description = "Tiempo SLA (Minutos)"


@admin.register(Aplicacion)
class AplicacionAdmin(admin.ModelAdmin):
    # No se toca esta clase, ya que Aplicacion todavía tiene el campo criticidad
    list_display = ('cod_aplicacion', 'nombre_aplicacion',
                    'bloque', 'criticidad', 'estado')
    list_filter = ('bloque', 'criticidad', 'estado')
    search_fields = ('cod_aplicacion', 'nombre_aplicacion')
    # Optimización: Carga los datos relacionados en una sola consulta.
    list_select_related = ('bloque', 'criticidad', 'estado')


@admin.register(CodigoCierre)
class CodigoCierreAdmin(admin.ModelAdmin):
    list_display = ('cod_cierre', 'desc_cod_cierre', 'aplicacion')
    list_filter = ('aplicacion',)
    search_fields = ('cod_cierre', 'desc_cod_cierre')
    # Optimización: Carga la aplicación relacionada en la misma consulta.
    list_select_related = ('aplicacion',)


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    # 3. Reemplazamos 'criticidad' por 'severidad'
    list_display = ('incidencia', 'aplicacion', 'estado',
                    'severidad', 'fecha_apertura', 'usuario_asignado')
    # 4. Reemplazamos 'criticidad' por 'severidad'
    list_filter = ('estado', 'severidad', 'aplicacion',
                   'grupo_resolutor', 'bloque')
    search_fields = ('incidencia', 'descripcion_incidencia',
                     'usuario_asignado')
    date_hierarchy = 'fecha_apertura'
    ordering = ('-fecha_apertura',)
    # Optimización: Carga todos los datos relacionados de una vez.
    list_select_related = ('aplicacion', 'estado', 'severidad',
                           'usuario_asignado', 'grupo_resolutor', 'bloque')
