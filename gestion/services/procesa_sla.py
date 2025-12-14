import configparser
from datetime import datetime, timedelta
import re
import csv
import os
import logging
import unicodedata
import mysql.connector


# --- Configuración del Logging (sin cambios) ---
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file_path = os.path.join(log_dir, "analizador_sla.log")

logging.basicConfig(
    level=logging.INFO,  # Cambiado a INFO para ver los logs de análisis
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# --- Funciones de Carga de Configuración y Utilitarios (sin cambios) ---


def cargar_configuracion(ruta_archivo="config.txt"):
    config = configparser.ConfigParser(allow_no_value=True, interpolation=None)
    config.read(ruta_archivo, encoding='utf-8')
    logger.info("Intentando cargar configuración desde: %s", ruta_archivo)
    config_data = {
        "grupos_gestores": {}, "severidad_incidencia_mapeo": {},
        "aplicacion_criticidad_mapeo": {}, "sla_combinado": {},
        "horario_laboral": {}, "dias_feriados": [], "db_config": {}
    }
    if 'GRUPOS_GESTORES' in config:
        for grupo, usuarios_str in config['GRUPOS_GESTORES'].items():
            if usuarios_str:
                config_data["grupos_gestores"][grupo.upper()] = [normalizar_texto(
                    u) for u in usuarios_str.split(',') if u.strip()]
    if 'SEVERIDAD_INCIDENCIA_MAPEO' in config:
        for id_crit, nombre_crit in config['SEVERIDAD_INCIDENCIA_MAPEO'].items():
            config_data["severidad_incidencia_mapeo"][int(
                id_crit)] = nombre_crit.strip()
    if 'APLICACION_CRITICIDAD_MAPEO' in config:
        for id_app, valor in config['APLICACION_CRITICIDAD_MAPEO'].items():
            partes = [p.strip() for p in valor.rsplit(',', 1)]
            if len(partes) == 2:
                config_data["aplicacion_criticidad_mapeo"][int(id_app)] = {
                    "nombre": partes[0], "criticidad": partes[1].lower()}
    if 'SLA_COMBINADO' in config:
        for clave, tiempo_str in config['SLA_COMBINADO'].items():
            partes = [p.strip() for p in clave.split(',')]
            h, m, s = map(int, tiempo_str.strip().split(':'))
            config_data["sla_combinado"][(partes[0].strip(), partes[1].strip(
            ).lower())] = timedelta(hours=h, minutes=m, seconds=s)
    if 'HORARIO_LABORAL' in config:
        for dia, horas_str in config['HORARIO_LABORAL'].items():
            if horas_str.upper() == 'CERRADO':
                config_data["horario_laboral"][dia.upper()] = None
            else:
                inicio_str, fin_str = horas_str.split('-')
                h_inicio, m_inicio = map(int, inicio_str.split(':'))
                h_fin, m_fin = map(int, fin_str.split(':'))
                config_data["horario_laboral"][dia.upper()] = (
                    h_inicio, m_inicio, h_fin, m_fin)
    if 'DIAS_FERIADOS' in config:
        for fecha_str, _ in config['DIAS_FERIADOS'].items():
            config_data["dias_feriados"].append(
                datetime.strptime(fecha_str, "%Y-%m-%d").date())
    if 'DATABASE_CONFIG' in config:
        config_data["db_config"] = {
            "host": config.get('DATABASE_CONFIG', 'DB_HOST'),
            "port": config.getint('DATABASE_CONFIG', 'DB_PORT'),
            "database": config.get('DATABASE_CONFIG', 'DB_NAME'),
            "user": config.get('DATABASE_CONFIG', 'DB_USER'),
            "password": config.get('DATABASE_CONFIG', 'DB_PASSWORD')
        }
    logger.info("Configuración cargada exitosamente.")
    return config_data


def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = re.sub(r'\s+', ' ', texto).strip().lower()
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


def is_working_time(dt_obj, horario_laboral, dias_feriados):
    if dt_obj.date() in dias_feriados:
        return False, None
    weekday_map = {0: 'LUNES', 1: 'MARTES', 2: 'MIERCOLES',
                   3: 'JUEVES', 4: 'VIERNES', 5: 'SABADO', 6: 'DOMINGO'}
    dia_semana_str = weekday_map.get(dt_obj.weekday())
    if dia_semana_str not in horario_laboral or horario_laboral[dia_semana_str] is None:
        return False, None
    h_inicio, m_inicio, h_fin, m_fin = horario_laboral[dia_semana_str]
    start_of_day = dt_obj.replace(
        hour=h_inicio, minute=m_inicio, second=0, microsecond=0)
    end_of_day = dt_obj.replace(
        hour=h_fin, minute=m_fin, second=0, microsecond=0)
    return start_of_day <= dt_obj < end_of_day, (start_of_day, end_of_day)


def calcular_tiempo_efectivo(start_dt, end_dt, horario_laboral, dias_feriados, es_critica_24_7=False):
    if start_dt >= end_dt:
        return timedelta(0)
    if es_critica_24_7:
        return end_dt - start_dt
    tiempo_laboral_total = timedelta(0)
    current_time = start_dt
    while not is_working_time(current_time, horario_laboral, dias_feriados)[0] and current_time < end_dt:
        current_time += timedelta(minutes=1)
    while current_time < end_dt:
        if is_working_time(current_time, horario_laboral, dias_feriados)[0]:
            tiempo_laboral_total += timedelta(minutes=1)
        current_time += timedelta(minutes=1)
    return tiempo_laboral_total


def parsear_bitacora(bitacora_texto, incidencia_id="N/A"):
    bitacora_texto_limpia = bitacora_texto.replace('¶', '\n')
    entries = []
    regex = re.compile(
        r'(\d{2}[-/]\d{2}[-/]\d{4} \d{1,2}:\d{2}:\d{2})\s*,\s*([^,]+?)\s*,\s*(.*?)(?=\s*[\r\n]+\s*[\xa0]?\d{2}[-/]\d{2}[-/]\d{4}|\Z)', re.DOTALL)
    matches = regex.finditer(bitacora_texto_limpia)
    for match in matches:
        date_str, user_raw, message = match.groups()
        try:
            dt_obj = datetime.strptime(date_str.replace(
                '/', '-').strip(), "%d-%m-%Y %H:%M:%S")
            entries.append({"fecha_hora": dt_obj, "usuario": normalizar_texto(
                user_raw), "mensaje": message.strip()})
        except ValueError:
            logger.warning(
                f"Error parseando fecha en bitácora para {incidencia_id}: '{date_str}'. Ignorando entrada.")
    entries.sort(key=lambda x: x["fecha_hora"])
    return entries

# --- Función Principal de Procesamiento (MODIFICADA) ---


def procesar_incidencias(ruta_incidencias_input, config_data):
    resultados_dict = {}
    incidencia_ids_a_procesar = []
    try:
        with open(ruta_incidencias_input, 'r', encoding='utf-8') as f:
            for line in f:
                inc_id = line.strip()
                if inc_id:
                    incidencia_ids_a_procesar.append(inc_id)
    except Exception as e:
        logger.critical(f"Error al leer IDs de incidencias: {e}")
        return []

    if not incidencia_ids_a_procesar:
        logger.warning("El archivo de incidencias está vacío.")
        return []

    db_conn = None
    try:
        db_config = config_data["db_config"]
        db_conn = mysql.connector.connect(**db_config)
        cursor = db_conn.cursor(dictionary=True)

        unique_ids = list(set(incidencia_ids_a_procesar))
        placeholders = ', '.join(['%s'] * len(unique_ids))
        query = f"SELECT incidencia, id_aplicacion, id_criticidad, fecha_ultima_resolucion, bitacora FROM INCIDENCIA WHERE incidencia IN ({placeholders})"

        cursor.execute(query, tuple(unique_ids))
        incidencias_from_db = {row['incidencia']                               : row for row in cursor.fetchall()}

        for inc_id in incidencia_ids_a_procesar:
            if inc_id not in incidencias_from_db:
                logger.warning(
                    f"Incidencia '{inc_id}' no encontrada en la base de datos.")
                resultados_dict[inc_id] = {
                    "incidencia": inc_id, "cumple_sla": "No Encontrada en DB"}
                continue

            row = incidencias_from_db[inc_id]
            incidencia = row["incidencia"]

            # --- INICIO DE LA LÓGICA DE CÁLCULO Y LOGS MEJORADA ---
            logger.info(
                f"\n--- Analizando Segmentos para Incidencia: {incidencia} ---")

            bitacora_texto = row.get("bitacora", "") or ""
            id_aplicacion = int(row["id_aplicacion"]) if row.get(
                "id_aplicacion") else None
            id_severidad_inc = int(row["id_criticidad"]) if row.get(
                "id_criticidad") else None

            severidad_incidencia = config_data["severidad_incidencia_mapeo"].get(
                id_severidad_inc, "Desconocida")
            app_info = config_data["aplicacion_criticidad_mapeo"].get(
                id_aplicacion, {})
            nombre_aplicativo = app_info.get("nombre", f"ID:{id_aplicacion}")
            criticidad_aplicativo = app_info.get("criticidad", "sin asignar")

            lista_gestores = config_data.get(
                "grupos_gestores", {}).get("GLOBAL_GROUP", [])
            bitacora_entries = parsear_bitacora(bitacora_texto, incidencia)
            tiempo_gestion_laboral_total_td = timedelta(0)
            es_critica_24_7 = (severidad_incidencia.lower() == "critica")

            ultimo_gestor = "N/A"
            if bitacora_entries:
                for entry in reversed(bitacora_entries):
                    if entry["usuario"] in lista_gestores:
                        ultimo_gestor = entry["usuario"]
                        break

            if len(bitacora_entries) > 1:
                for j in range(len(bitacora_entries) - 1):
                    current_entry, next_entry = bitacora_entries[j], bitacora_entries[j+1]

                    segment_start_str = current_entry['fecha_hora'].strftime(
                        '%d-%m-%Y %H:%M:%S')
                    segment_end_str = next_entry['fecha_hora'].strftime(
                        '%d-%m-%Y %H:%M:%S')
                    start_user = current_entry['usuario']
                    end_user = next_entry['usuario']

                    logger.info(
                        f"Desde {segment_start_str} hasta {segment_end_str}.")
                    logger.info(f"-> De: '{start_user}' | A: '{end_user}'")

                    if end_user in lista_gestores and 'pendiente' not in current_entry['mensaje'].lower():
                        tiempo_segmento = calcular_tiempo_efectivo(
                            current_entry["fecha_hora"], next_entry["fecha_hora"],
                            config_data["horario_laboral"], config_data["dias_feriados"], es_critica_24_7
                        )
                        tiempo_gestion_laboral_total_td += tiempo_segmento
                        logger.info(
                            f"✅ ANÁLISIS: Se cuenta el tiempo. Gestor '{end_user}' respondió. Tiempo sumado: {str(tiempo_segmento)}")
                    else:
                        if end_user not in lista_gestores:
                            logger.info(
                                f"❌ ANÁLISIS: No se cuenta. El usuario '{end_user}' no es un gestor.")
                        elif 'pendiente' in current_entry['mensaje'].lower():
                            logger.info(
                                f"⏸️ ANÁLISIS: No se cuenta. El reloj está pausado por nota 'Pendiente' de '{start_user}'.")
                    logger.info("-" * 60)

            # --- FIN DE LA LÓGICA DE CÁLCULO Y LOGS MEJORADA ---

            if tiempo_gestion_laboral_total_td == timedelta(0) and not es_critica_24_7 and bitacora_entries:
                tiempo_gestion_laboral_total_td = timedelta(minutes=20)
                logger.info(
                    "-> Aplicando fallback de 20 minutos por tiempo de gestión 0.")

            tiempo_gestion_segundos = int(
                tiempo_gestion_laboral_total_td.total_seconds())
            h, rem = divmod(tiempo_gestion_segundos, 3600)
            tiempo_gestion_horas_str = f"{h:02d}:{rem//60:02d}:{rem % 60:02d}"
            logger.info(
                f"-> TIEMPO TOTAL DE GESTIÓN PARA {incidencia}: {tiempo_gestion_horas_str}\n")

            fecha_resolucion = row.get("fecha_ultima_resolucion")
            fecha_resolucion_str = fecha_resolucion.strftime(
                '%Y-%m-%d %H:%M:%S') if isinstance(fecha_resolucion, datetime) else "N/A"

            sla_key = (normalizar_texto(severidad_incidencia),
                       normalizar_texto(criticidad_aplicativo))
            sla_timedelta = config_data["sla_combinado"].get(sla_key)
            sla_total_segundos, sla_total_horas_str = "N/A", "N/A"
            if sla_timedelta:
                sla_total_segundos = int(sla_timedelta.total_seconds())
                h_sla, rem_sla = divmod(sla_total_segundos, 3600)
                sla_total_horas_str = f"{h_sla:02d}:{rem_sla//60:02d}:{rem_sla % 60:02d}"

            cumple_sla = ""
            if criticidad_aplicativo == "sin asignar":
                cumple_sla = "SLA No Calculado (Criticidad Aplicativo 'sin asignar')"
            elif not sla_timedelta:
                cumple_sla = "SLA No Definido para esta combinación"
            elif not bitacora_entries:
                cumple_sla = "SLA No Calculado (Bitácora no parseable)"
            else:
                cumple_sla = "Sí" if tiempo_gestion_segundos <= sla_total_segundos else "No"

            resultados_dict[incidencia] = {
                "incidencia": incidencia, "fecha_ultima_resolucion": fecha_resolucion_str,
                "usuario": ultimo_gestor, "aplicativo": nombre_aplicativo,
                "criticidad_aplicativo": criticidad_aplicativo, "severidad": severidad_incidencia,
                "sla_total_segundos": sla_total_segundos, "sla_total_horas": sla_total_horas_str,
                "tiempo_gestion_laboral_segundos": tiempo_gestion_segundos,
                "tiempo_gestion_laboral_horas": tiempo_gestion_horas_str,
                "cumple_sla": cumple_sla
            }

    except mysql.connector.Error as err:
        logger.critical(f"Error de base de datos: {err}")
    except Exception as e:
        logger.critical(f"Ocurrió un error inesperado: {e}")
    finally:
        if db_conn and db_conn.is_connected():
            cursor.close()
            db_conn.close()
            logger.info("Conexión a la base de datos cerrada.")

    return [resultados_dict.get(inc_id) for inc_id in incidencia_ids_a_procesar if inc_id in resultados_dict]


def guardar_resultados_csv(resultados, nombre_archivo="reporte_sla_incidencias.csv"):
    if not resultados:
        logger.info("No hay resultados para guardar.")
        return
    fieldnames = [
        "incidencia", "fecha_ultima_resolucion", "usuario", "aplicativo", "criticidad_aplicativo",
        "severidad", "sla_total_segundos", "sla_total_horas", "tiempo_gestion_laboral_segundos",
        "tiempo_gestion_laboral_horas", "cumple_sla"
    ]
    try:
        with open(nombre_archivo, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(resultados)
        logger.info(f"Reporte generado exitosamente en '{nombre_archivo}'")
    except IOError as e:
        logger.error(
            f"Error al escribir el archivo CSV '{nombre_archivo}': {e}")


# --- Ejecución Principal (sin cambios) ---
if __name__ == "__main__":
    ruta_incidencias_input_ids = "incidencias.txt"
    ruta_config = "config.txt"

    if not os.path.exists(ruta_incidencias_input_ids):
        logger.error(
            f"Error fatal: El archivo de IDs '{ruta_incidencias_input_ids}' no se encontró.")
        exit(1)
    if not os.path.exists(ruta_config):
        logger.error(
            f"Error fatal: El archivo de configuración '{ruta_config}' no se encontró.")
        exit(1)

    logger.info(
        "Iniciando el proceso de análisis de SLA desde la Base de Datos (con lógica 'Pendiente').")
    configuracion = cargar_configuracion(ruta_config)

    if not configuracion.get("db_config"):
        logger.critical(
            "La configuración [DATABASE_CONFIG] es necesaria en config.txt.")
        exit(1)

    resultados_analisis = procesar_incidencias(
        ruta_incidencias_input_ids, configuracion)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_csv_path = f"reporte_sla_DB_{timestamp}.csv"
    guardar_resultados_csv(resultados_analisis, reporte_csv_path)

    if resultados_analisis:
        stats = {"Sí": 0, "No": 0, "No Encontrada en DB": 0}
        for res in resultados_analisis:
            estado = res.get("cumple_sla", "Otro")
            if estado in stats:
                stats[estado] += 1
            else:
                stats.setdefault(estado, 0)
                stats[estado] += 1

        logger.info("\n--- RESUMEN DE ESTADÍSTICAS DE SLA ---")
        for estado, count in stats.items():
            logger.info(f"{estado:<40} : {count}")
        logger.info(
            f"{'Total de incidencias procesadas':<40} : {len(resultados_analisis)}")
        logger.info("-------------------------------------")

    logger.info("Proceso de análisis de SLA completado.")
