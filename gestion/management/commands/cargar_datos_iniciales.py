# gestion/management/commands/cargar_datos_iniciales.py

from django.core.management.base import BaseCommand
from django.db import transaction
from gestion.models import (
    Usuario, Estado, Impacto, Interfaz, Severidad, Bloque,
    GrupoResolutor, DiaFeriado, HorarioLaboral, ReglaSLA, Criticidad, Cluster
)
from datetime import datetime, time, timedelta


class Command(BaseCommand):
    help = 'Carga los datos iniciales de todas las tablas catálogo en la base de datos, manteniendo los IDs específicos.'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(
            "--- Iniciando la carga de datos iniciales ---"))

        # --- Cargando Usuarios ---
        self.stdout.write("Cargando Usuarios...")
        usuarios_data = [
            {'id': 1, 'usuario': 'ind_bllacc',
                'nombre': 'BETSY LLACCHUARIMAY DE LA CRUZ', 'habilitado': False},
            {'id': 2, 'usuario': 'ind_dcorra',
                'nombre': 'DAVID AARON CORRALES OLIVARES', 'habilitado': True},
            {'id': 3, 'usuario': 'ind_msalas',
                'nombre': 'MARCO ANTONIO SALAS ESCANILLA', 'habilitado': True},
            {'id': 4, 'usuario': 'ind_smunoz',
                'nombre': 'SEBASTIAN NICOLAS MUÑOZ GARCIA', 'habilitado': True},
            {'id': 5, 'usuario': 'ind_jecocp',
                'nombre': 'JOSE COCHE PIUTRIN', 'habilitado': True},
            {'id': 6, 'usuario': 'ind_wsilva',
                'nombre': 'WALTER HAROL SILVA GONZÁLEZ', 'habilitado': True},
            {'id': 7, 'usuario': 'ind_rarane',
                'nombre': 'RUBEN OSVALDO ARANEDA SALAZAR', 'habilitado': True},
            {'id': 8, 'usuario': 'ind_camaga',
                'nombre': 'CHRISTIAN ARTURO MAGAÑA RUIZ', 'habilitado': False},
            {'id': 9, 'usuario': 'ind_caranc',
                'nombre': 'CARLOS HERNAN ARANCIBIA OYARCE', 'habilitado': True},
            {'id': 10, 'usuario': 'ind_ojagar',
                'nombre': 'Ojagar', 'habilitado': True},
            {'id': 11, 'usuario': 'ind_esaave',
                'nombre': 'EMILIO ANDRÉS SAAVEDRA TOBAR', 'habilitado': True},
            {'id': 12, 'usuario': 'ind_ghuama',
                'nombre': 'GEAN FRANKS JERALD HUAMAN SOLIS', 'habilitado': True},
            {'id': 13, 'usuario': 'ind_jhenri',
                'nombre': 'JORGE ANDRES HENRIQUEZ QUEZADA', 'habilitado': True},
            {'id': 14, 'usuario': 'jcmanosalva',
                'nombre': 'JUAN CARLOS MANOSALVA FUENTES', 'habilitado': True},
            {'id': 15, 'usuario': 'ind_vasero',
                'nombre': 'VANESSA SEPULVEDA ROJAS', 'habilitado': True},
            {'id': 16, 'usuario': 'ind_greyes',
                'nombre': 'GUSTAVO REYES ROMERO', 'habilitado': True},
        ]
        for data in usuarios_data:
            obj_id = data.pop('id')
            Usuario.objects.update_or_create(id=obj_id, defaults=data)
        self.stdout.write(self.style.SUCCESS(
            "✅ Usuarios cargados/actualizados."))

        # --- Cargando Estados ---
        self.stdout.write("Cargando Estados...")
        estados_data = [
            {'id': 1, 'desc_estado': 'Construccion', 'uso_estado': 'Aplicacion'},
            {'id': 2, 'desc_estado': 'Produccion', 'uso_estado': 'Aplicacion'},
            {'id': 3, 'desc_estado': 'Deshuso', 'uso_estado': 'Aplicacion'},
            {'id': 4, 'desc_estado': 'Pendiente', 'uso_estado': 'Incidencia'},
            {'id': 5, 'desc_estado': 'Resuelto', 'uso_estado': 'Incidencia'},
            {'id': 6, 'desc_estado': 'Cerrado', 'uso_estado': 'Incidencia'},
            {'id': 7, 'desc_estado': 'Cancelado', 'uso_estado': 'Incidencia'},
        ]
        for data in estados_data:
            obj_id = data.pop('id')
            Estado.objects.update_or_create(id=obj_id, defaults=data)
        self.stdout.write(self.style.SUCCESS(
            "✅ Estados cargados/actualizados."))

        # --- Cargando Impactos ---
        self.stdout.write("Cargando Impactos...")
        impactos_data = [
            {'id': 1, 'desc_impacto': 'interno'},
            {'id': 2, 'desc_impacto': 'externo'},
            {'id': 3, 'desc_impacto': 'sin definir'},
        ]
        for data in impactos_data:
            obj_id = data.pop('id')
            Impacto.objects.update_or_create(id=obj_id, defaults=data)
        self.stdout.write(self.style.SUCCESS(
            "✅ Impactos cargados/actualizados."))

        # --- Cargando Interfaces ---
        self.stdout.write("Cargando Interfaces...")
        interfaces_data = [(1, 'No definida'), (2, 'WEB'), (3, 'Tabla'), (4, 'Sin servicio'), (5, 'Sin despliegue de información'), (6, 'Sin activación'), (7, 'Sin acceso'), (8, 'SERVIDOR'), (9, 'Reporte'), (10, 'PRODUCTOS PS'), (11, 'Proceso'), (12, 'Portabilidad'), (13, 'Peticiones sin aplicar'), (14, 'Normalización y factibilidad técnica multiservicio'),
                           (15, 'Infraestructura'), (16, 'Indisponibilidad PMS'), (17, 'Inconsistencia de datos'), (18, 'FTP'), (19, 'Frontend'), (20, 'Cuenta'), (21, 'Contención'), (22, 'Consumo de CPU'), (23, 'Cancelación de proceso'), (24, 'Base de datos'), (25, 'BACKEND'), (26, 'Archivo'), (27, 'Aplicativo'), (28, 'Agenda WEB')]
        for obj_id, desc in interfaces_data:
            Interfaz.objects.update_or_create(
                id=obj_id, defaults={'desc_interfaz': desc})
        self.stdout.write(self.style.SUCCESS(
            "✅ Interfaces cargadas/actualizadas."))

        # --- Cargando Severidades ---
        self.stdout.write("Cargando Severidades...")
        severidades_data = [(1, 'critica'), (2, 'alta'),
                            (3, 'media'), (4, 'baja'), (5, 'sin prioridad')]
        for obj_id, desc in severidades_data:
            Severidad.objects.update_or_create(
                id=obj_id, defaults={'desc_severidad': desc})
        self.stdout.write(self.style.SUCCESS(
            "✅ Severidades cargadas/actualizadas."))

        # --- Cargando Bloques ---
        self.stdout.write("Cargando Bloques...")
        bloques_data = [(1, 'BLOQUE 1'), (2, 'BLOQUE 2'),
                        (3, 'BLOQUE 3'), (4, 'BLOQUE 4'), (5, 'Sin bloque')]
        for obj_id, desc in bloques_data:
            Bloque.objects.update_or_create(
                id=obj_id, defaults={'desc_bloque': desc})
        self.stdout.write(self.style.SUCCESS(
            "✅ Bloques cargados/actualizados."))

        # --- Cargando Grupos Resolutores ---
        self.stdout.write("Cargando Grupos Resolutores...")
        grupos_data = [(1, 'grupo_generico'), (2, 'Everis N2'), (3, 'HP-SPN'), (4, 'ACC N2'), (5, 'AMDOCS N2'), (7, 'INDRA N2'), (8, 'Soporte DWH G11'), (9, 'SOPORTE DWH MOVIL'),
                       (10, 'Soporte Génesis G1'), (11, 'SWF_INDRA_G1'), (12, 'SWF_INDRA_G11'), (13, 'SWF_INDRA_G3'), (14, 'SWF_INDRA_G5'), (15, 'SWF_INDRA_3B'), (16, 'INDRA_D')]
        for obj_id, desc in grupos_data:
            GrupoResolutor.objects.update_or_create(
                id=obj_id, defaults={'desc_grupo_resol': desc})
        self.stdout.write(self.style.SUCCESS(
            "✅ Grupos Resolutores cargados/actualizados."))

        # --- Cargando Días Feriados ---
        self.stdout.write("Cargando Días Feriados...")
        feriados_data = [
            {'id': 1, 'fecha': '2025-06-20',
                'descripcion': 'Día Nacional de los Pueblos Indígenas'},
            {'id': 2, 'fecha': '2025-07-16',
                'descripcion': 'Día de la Virgen del Carmen'},
            {'id': 3, 'fecha': '2025-08-15', 'descripcion': 'Asunción de la Virgen'},
            {'id': 4, 'fecha': '2025-09-18', 'descripcion': 'Independencia Nacional'},
            {'id': 5, 'fecha': '2025-09-19',
                'descripcion': 'Día de las Glorias del Ejército'},
            {'id': 6, 'fecha': '2025-10-12',
                'descripcion': 'Encuentro de Dos Mundos'},
            {'id': 7, 'fecha': '2025-10-31',
                'descripcion': 'Día de las Iglesias Evangélicas y Protestantes'},
            {'id': 8, 'fecha': '2025-11-01',
                'descripcion': 'Día de Todos los Santos'},
            {'id': 9, 'fecha': '2025-11-16', 'descripcion': 'Feriado Ejemplo'},
            {'id': 10, 'fecha': '2025-12-08',
                'descripcion': 'Inmaculada Concepción'},
            {'id': 11, 'fecha': '2025-12-25', 'descripcion': 'Navidad'},
        ]
        for data in feriados_data:
            obj_id = data.pop('id')
            data['fecha'] = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
            DiaFeriado.objects.update_or_create(id=obj_id, defaults=data)
        self.stdout.write(self.style.SUCCESS(
            "✅ Días Feriados cargados/actualizados."))

        # --- Cargando Horario Laboral ---
        self.stdout.write("Cargando Horario Laboral...")
        horarios_data = [
            {'id': 1, 'dia_semana': 0, 'hora_inicio': time(
                9, 0), 'hora_fin': time(18, 0)},
            {'id': 2, 'dia_semana': 1, 'hora_inicio': time(
                9, 0), 'hora_fin': time(18, 0)},
            {'id': 3, 'dia_semana': 2, 'hora_inicio': time(
                9, 0), 'hora_fin': time(18, 0)},
            {'id': 4, 'dia_semana': 3, 'hora_inicio': time(
                9, 0), 'hora_fin': time(18, 0)},
            {'id': 5, 'dia_semana': 4, 'hora_inicio': time(
                9, 0), 'hora_fin': time(18, 0)},
            {'id': 6, 'dia_semana': 5, 'hora_inicio': None, 'hora_fin': None},
            {'id': 7, 'dia_semana': 6, 'hora_inicio': None, 'hora_fin': None},
        ]
        for data in horarios_data:
            obj_id = data.pop('id')
            HorarioLaboral.objects.update_or_create(id=obj_id, defaults=data)
        self.stdout.write(self.style.SUCCESS(
            "✅ Horarios Laborales cargados/actualizados."))

        # --- Cargando Clusters ---
        self.stdout.write("Cargando Clusters...")
        clusters_data = [(1, 'Datos'), (2, 'SW'), (3, 'Reproceso'), (4, 'Apoyo Infraestructura'), (5, 'Apoyo Configuración'), (6, 'Apoyo Usuario'), (7, 'Apoyo Procedimiento Comercial'), (
            8, 'Apoyo Control-M'), (9, 'Apoyo Contenida en IT'), (10, 'Apoyo Proveedor sin Soporte TI'), (11, 'Apoyo (Otra Casuística)'), (12, 'Apoyo No Replica en Producción'), (13, 'Sin Cluster')]
        for obj_id, desc in clusters_data:
            Cluster.objects.update_or_create(
                id=obj_id, defaults={'desc_cluster': desc})
        self.stdout.write(self.style.SUCCESS(
            "✅ Clusters cargados/actualizados."))

        # --- Cargando Criticidades (necesario para Reglas SLA) ---
        self.stdout.write("Cargando Criticidades...")
        Criticidad.objects.update_or_create(
            id=1, defaults={'desc_criticidad': 'critica'})
        Criticidad.objects.update_or_create(
            id=2, defaults={'desc_criticidad': 'no critica'})
        self.stdout.write(self.style.SUCCESS(
            "✅ Criticidades cargadas/actualizadas."))

        # --- Cargando Reglas de SLA ---
        self.stdout.write("Cargando Reglas de SLA...")
        reglas_data = [
            {'id': 1, 'tiempo_sla': timedelta(
                hours=4), 'criticidad_aplicacion_id': 1, 'severidad_id': 1},
            {'id': 2, 'tiempo_sla': timedelta(
                hours=28), 'criticidad_aplicacion_id': 2, 'severidad_id': 1},
            {'id': 3, 'tiempo_sla': timedelta(
                hours=5), 'criticidad_aplicacion_id': 1, 'severidad_id': 2},
            {'id': 4, 'tiempo_sla': timedelta(
                hours=18), 'criticidad_aplicacion_id': 2, 'severidad_id': 2},
            {'id': 5, 'tiempo_sla': timedelta(
                hours=12), 'criticidad_aplicacion_id': 1, 'severidad_id': 3},
            {'id': 6, 'tiempo_sla': timedelta(
                hours=48), 'criticidad_aplicacion_id': 2, 'severidad_id': 3},
            {'id': 7, 'tiempo_sla': timedelta(
                hours=40), 'criticidad_aplicacion_id': 1, 'severidad_id': 4},
            {'id': 8, 'tiempo_sla': timedelta(
                hours=80), 'criticidad_aplicacion_id': 2, 'severidad_id': 4},
            {'id': 9, 'tiempo_sla': timedelta(
                hours=96), 'criticidad_aplicacion_id': 1, 'severidad_id': 5},
            {'id': 10, 'tiempo_sla': timedelta(
                hours=96), 'criticidad_aplicacion_id': 2, 'severidad_id': 5},
        ]
        for data in reglas_data:
            obj_id = data.pop('id')
            ReglaSLA.objects.update_or_create(id=obj_id, defaults=data)
        self.stdout.write(self.style.SUCCESS(
            "✅ Reglas SLA cargadas/actualizadas."))

        self.stdout.write(self.style.SUCCESS(
            "\n🎉 ¡Proceso de carga de datos iniciales finalizado! 🎉"))
