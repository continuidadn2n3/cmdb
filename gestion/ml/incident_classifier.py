# gestion/ml/incident_classifier.py

import joblib
from django.conf import settings
from gestion.models import CodigoCierre, Incidencia
from sklearn.feature_extraction.text import TfidfVectorizer
import logging


def normalizar_texto(texto):
    """Una función simple para limpiar y normalizar texto."""
    if not texto:
        return ""
    return texto.lower().strip()


logger = logging.getLogger(__name__)

# Definimos la ruta donde se guardará el modelo entrenado
MODEL_PATH = settings.BASE_DIR / "gestion" / "ml" / "similarity_model.joblib"


def build_and_save_similarity_model():
    """
    Carga todos los CodigoCierre, los vectoriza y guarda el modelo para búsqueda de similitud.
    Modo Híbrido: Incluye historial de incidencias reales.
    """
    # 1. Cargar datos desde la base de datos
    codigos = CodigoCierre.objects.select_related('aplicacion').all()

    if not codigos.exists():
        logger.warning(
            "No hay códigos de cierre en la base de datos para construir el modelo de similitud.")
        return

    # 2. Preparar los textos (Modo Híbrido)
    corpus = []
    code_ids = []
    code_to_app_map = {}

    logger.info(f"Iniciando entrenamiento híbrido con {codigos.count()} códigos...")

    for c in codigos:
        # Texto base (Definición teórica)
        texto_base = f"{c.desc_cod_cierre} {c.causa_cierre}"
        
        # Texto histórico (Evidencia práctica)
        # Limitamos a 50 últimas incidencias para balancear rendimiento y relevancia
        incidencias = Incidencia.objects.filter(codigo_cierre=c).order_by('-fecha_apertura')[:50]
        
        texto_historial = " ".join([
            f"{inc.descripcion_incidencia or ''} {inc.causa or ''} {inc.solucion_final or ''} {inc.observaciones or ''}"
            for inc in incidencias
        ])
        
        # Combinar y normalizar
        texto_completo = normalizar_texto(f"{texto_base} {texto_historial}")
        
        corpus.append(texto_completo)
        code_ids.append(c.id)
        code_to_app_map[c.id] = [c.aplicacion.id] if c.aplicacion else []

    # 3. Crear y "entrenar" el vectorizador
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(
        1, 2), stop_words='english')

    logger.info("Construyendo la matriz de vectores de los códigos de cierre...")
    tfidf_matrix = vectorizer.fit_transform(corpus)

    # 4. Guardar los componentes necesarios para la búsqueda
    model_data = {
        'vectorizer': vectorizer,
        'tfidf_matrix': tfidf_matrix,
        'code_ids': code_ids,
        'code_to_app_map': code_to_app_map
    }

    joblib.dump(model_data, MODEL_PATH)
    logger.info(f"Modelo de similitud guardado exitosamente en: {MODEL_PATH}")
