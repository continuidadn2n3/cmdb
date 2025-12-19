from django.db import models
from django.contrib.auth.models import User

# Modelos de tablas catálogo (simples)


class Bloque(models.Model):
    desc_bloque = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.desc_bloque


class Cluster(models.Model):
    desc_cluster = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.desc_cluster


class Criticidad(models.Model):
    desc_criticidad = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.desc_criticidad


class Severidad(models.Model):
    desc_severidad = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.desc_severidad


class GrupoResolutor(models.Model):
    desc_grupo_resol = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.desc_grupo_resol


class Impacto(models.Model):
    desc_impacto = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.desc_impacto


class Estado(models.Model):
    class UsoChoices(models.TextChoices):
        INCIDENCIA = 'Incidencia', 'Incidencia'
        APLICACION = 'Aplicacion', 'Aplicacion'

    desc_estado = models.CharField(max_length=100, unique=True)
    uso_estado = models.CharField(
        max_length=50, choices=UsoChoices.choices, blank=True, verbose_name="Uso del Estado",
        help_text="Selecciona dónde se utiliza principalmente este estado.")

    def __str__(self) -> str:
        return self.desc_estado


class Interfaz(models.Model):
    desc_interfaz = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.desc_interfaz

# Modelos con relaciones


class Aplicacion(models.Model):
    cod_aplicacion = models.CharField(max_length=50, unique=True)
    nombre_aplicacion = models.CharField(max_length=255)
    desc_aplicacion = models.TextField(blank=True, null=True)

    # Relaciones
    bloque = models.ForeignKey(
        Bloque, on_delete=models.PROTECT, null=True, blank=True)
    criticidad = models.ForeignKey(
        Criticidad, on_delete=models.PROTECT, null=True, blank=True)
    estado = models.ForeignKey(
        Estado, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.cod_aplicacion} - {self.nombre_aplicacion}"


class CodigoCierre(models.Model):
    cod_cierre = models.CharField(max_length=50)
    desc_cod_cierre = models.TextField(blank=True, default='')
    causa_cierre = models.TextField(blank=True, default='')

    # Relación
    aplicacion = models.ForeignKey(
        Aplicacion, on_delete=models.CASCADE, related_name='codigos_cierre')

    class Meta:
        # Asegura que la combinación de código y aplicación sea única.
        unique_together = ('cod_cierre', 'aplicacion')

    def __str__(self) -> str:
        return self.cod_cierre


class Incidencia(models.Model):
    # El ID automático será creado por Django.
    incidencia = models.CharField(max_length=50, unique=True)

    # Campos de texto y fecha
    descripcion_incidencia = models.TextField(blank=True)

    fecha_apertura = models.DateTimeField(null=True, blank=True)
    fecha_ultima_resolucion = models.DateTimeField(null=True, blank=True)

    causa = models.TextField(blank=True)
    bitacora = models.TextField(blank=True)
    tec_analisis = models.TextField(blank=True)
    correccion = models.TextField(blank=True)
    solucion_final = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)

    class Workaround(models.TextChoices):
        NO = 'No', 'No'
        SI = 'Sí', 'Sí'

    demandas = models.TextField(null=True, blank=True)
    workaround = models.CharField(
        max_length=2, choices=Workaround.choices, default=Workaround.NO)

    # Relaciones (ForeignKey)
    aplicacion = models.ForeignKey(
        Aplicacion,
        on_delete=models.CASCADE,
        related_name='incidencias',
        null=True,
        blank=True
    )
    estado = models.ForeignKey(
        Estado, on_delete=models.PROTECT, related_name='incidencias'
    )
    severidad = models.ForeignKey(
        Severidad,
        on_delete=models.PROTECT,
        related_name='incidencias',
        null=True,
        blank=True
    )
    grupo_resolutor = models.ForeignKey(
        GrupoResolutor, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias_resueltas'
    )
    interfaz = models.ForeignKey(
        Interfaz, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias'
    )
    impacto = models.ForeignKey(
        Impacto, on_delete=models.PROTECT, related_name='incidencias'
    )
    cluster = models.ForeignKey(
        Cluster, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias'
    )
    bloque = models.ForeignKey(
        Bloque,
        on_delete=models.PROTECT,
        related_name='incidencias',
        null=True,
        blank=True
    )
    codigo_cierre = models.ForeignKey(
        CodigoCierre, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias'
    )
    usuario_asignado = models.ForeignKey(
        'Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias_asignadas'
    )
    cumple_sla = models.CharField(
        max_length=50,
        choices=[('Sí', 'Sí'), ('No', 'No'), ('N/A', 'No Aplica')],
        default='N/A',
        blank=True,
        null=True,
        verbose_name="Cumple SLA"
    )
    tiempo_sla_calculado = models.DurationField(
        blank=True,
        null=True,
        help_text="Tiempo de gestión laboral calculado para el SLA.",
        verbose_name="Tiempo de Gestión (SLA)"
    )

    # Campos de Auditoría
    usuario_creador = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidencias_creadas',
        verbose_name="Creado por"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )

    def __str__(self) -> str:
        return self.incidencia

    class Meta:
        verbose_name = "Incidencia"
        verbose_name_plural = "Incidencias"
        ordering = ['-fecha_apertura']


class Usuario(models.Model):
    # Django añade automáticamente un campo 'id' que es una clave primaria auto-incremental.
    # El nombre de la tabla en la base de datos será 'gestion_usuario' por defecto.
    usuario = models.CharField(max_length=150, unique=True)
    nombre = models.CharField(max_length=255)
    habilitado = models.BooleanField(default=True, verbose_name="Habilitado")

    def __str__(self) -> str:
        return f"{self.usuario}{'' if self.habilitado else ' (Deshabilitado)'}"


class ReglaSLA(models.Model):
    # Relaciones para la combinación
    severidad = models.ForeignKey(Severidad, on_delete=models.CASCADE)
    criticidad_aplicacion = models.ForeignKey(
        Criticidad, on_delete=models.CASCADE)

    # El tiempo de SLA
    tiempo_sla = models.DurationField(
        help_text="Tiempo máximo de resolución en formato DD HH:MM:SS"
    )

    @property
    def tiempo_sla_segundos(self) -> int:
        """Devuelve el tiempo total de SLA en segundos."""
        if not self.tiempo_sla:
            return 0
        return int(self.tiempo_sla.total_seconds())

    @property
    def tiempo_sla_horas(self) -> str:
        """Devuelve el tiempo de SLA formateado como HH:MM:SS."""
        if not self.tiempo_sla:
            return "00:00:00"
        total_seconds = int(self.tiempo_sla.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def __str__(self) -> str:
        return f"SLA para {self.severidad} en App {self.criticidad_aplicacion}: {self.tiempo_sla}"

    class Meta:
        # Asegura que no haya reglas duplicadas para la misma combinación
        unique_together = ('severidad', 'criticidad_aplicacion')
        verbose_name = "Regla de SLA"
        verbose_name_plural = "Reglas de SLA"


class HorarioLaboral(models.Model):
    DIA_CHOICES = [
        (0, 'LUNES'), (1, 'MARTES'), (2, 'MIÉRCOLES'),
        (3, 'JUEVES'), (4, 'VIERNES'), (5, 'SÁBADO'), (6, 'DOMINGO')
    ]
    dia_semana = models.IntegerField(choices=DIA_CHOICES, unique=True)
    hora_inicio = models.TimeField(
        null=True, blank=True, help_text="Dejar en blanco si es un día no laboral (CERRADO)")
    hora_fin = models.TimeField(null=True, blank=True)

    def __str__(self) -> str:
        if self.hora_inicio and self.hora_fin:
            return f"{self.get_dia_semana_display()}: {self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')}"
        return f"{self.get_dia_semana_display()}: CERRADO"

    class Meta:
        ordering = ['dia_semana']
        verbose_name = "Horario Laboral"
        verbose_name_plural = "Horarios Laborales"


class DiaFeriado(models.Model):
    fecha = models.DateField(unique=True, help_text="Fecha del día feriado.")
    descripcion = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"{self.fecha.strftime('%Y-%m-%d')} - {self.descripcion}"

    class Meta:
        ordering = ['fecha']
        verbose_name = "Día Feriado"
        verbose_name_plural = "Días Feriados"
