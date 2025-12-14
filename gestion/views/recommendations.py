import joblib
import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from sklearn.metrics.pairwise import cosine_similarity

from django.contrib.auth.decorators import login_required, user_passes_test
from gestion.models import CodigoCierre, Aplicacion
from gestion.ml.incident_classifier import normalizar_texto, MODEL_PATH, build_and_save_similarity_model

logger = logging.getLogger(__name__)

# --- Lógica de recomendación ---


def load_model():
    """Carga el modelo de similitud desde el archivo."""
    try:
        model_data = joblib.load(MODEL_PATH)
        logger.info("Modelo de similitud cargado correctamente.")
        return model_data
    except FileNotFoundError:
        logger.error(
            f"No se encontró el archivo del modelo en {MODEL_PATH}. Ejecuta 'python manage.py train_incident_classifier' para crearlo.")
        return None
    except Exception as e:
        logger.error(f"Error al cargar el modelo de similitud: {e}")
        return None


SIMILARITY_MODEL_DATA = load_model()
# Umbral de similitud (ajustar según sea necesario, 20% es un buen punto de partida)
SIMILARITY_THRESHOLD = 0.20


def recommendation_test_page(request):
    """
    Renderiza una página HTML para probar el sistema de recomendación.
    """
    # Ordenamos las aplicaciones por nombre para que aparezcan en orden alfabético en el dropdown
    aplicaciones = Aplicacion.objects.order_by('nombre_aplicacion')
    context = {'aplicaciones': aplicaciones}
    return render(request, 'gestion/recommendation_test.html', context)


@login_required
def reentrenar_modelo_view(request):
    """
    Vista para forzar el re-entrenamiento del modelo de similitud.
    """
    if request.method != 'POST':
         return JsonResponse({'status': 'error', 'message': 'Método no permitido.'}, status=405)
    
    try:
        logger.info("Iniciando re-entrenamiento manual del modelo...")
        build_and_save_similarity_model()
        
        # Recargar el modelo en memoria global
        global SIMILARITY_MODEL_DATA
        SIMILARITY_MODEL_DATA = load_model()
        
        return JsonResponse({'status': 'success', 'message': 'Modelo re-entrenado y recargado exitosamente.'})
    except Exception as e:
        logger.error(f"Error durante el re-entrenamiento manual: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'Error al re-entrenar el modelo: {str(e)}'}, status=500)


@require_POST
def recommend_closure_code_view(request):
    """
    Recibe una descripción y busca los 3 CodigoCierre más similares en la base de conocimiento.
    """
    global SIMILARITY_MODEL_DATA
    if not SIMILARITY_MODEL_DATA:
        # Intentar cargar si estaba vacío (por si falló al inicio pero ya se creó)
        SIMILARITY_MODEL_DATA = load_model()
        if not SIMILARITY_MODEL_DATA:
            return JsonResponse({'status': 'error', 'message': 'El servicio de recomendación no está disponible.'}, status=503)

    # Log #1: Confirmamos que la vista se está ejecutando en cuanto llega una petición.
    logger.info("recommend_closure_code_view: Vista iniciada.")

    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error(
                "Error: El cuerpo de la solicitud no es un JSON válido.")
            return JsonResponse({'status': 'error', 'message': 'El formato de la solicitud es incorrecto (no es JSON).'}, status=400)

        description = data.get('description', '')
        application_id = data.get('application_id')

        logger.info(
            f"Solicitud procesada. App ID: {application_id}, Descripción: '{description[:50]}...'")

        if not description:
            return JsonResponse({'status': 'error', 'message': 'La descripción no puede estar vacía.'}, status=400)

        # Extraer componentes del modelo
        vectorizer = SIMILARITY_MODEL_DATA['vectorizer']
        tfidf_matrix = SIMILARITY_MODEL_DATA['tfidf_matrix']
        all_code_ids = SIMILARITY_MODEL_DATA['code_ids']
        code_to_app_map = SIMILARITY_MODEL_DATA.get('code_to_app_map', {})

        # --- Filtrar por aplicativo ---
        indices_to_search = list(range(len(all_code_ids)))
        code_ids_to_search = all_code_ids

        if application_id and code_to_app_map:
            logger.debug(f"Filtrando por application_id: {application_id}")
            filtered_indices = []
            filtered_code_ids = []
            for i, code_id in enumerate(all_code_ids):
                app_list = code_to_app_map.get(code_id, [])
                if not app_list or int(application_id) in app_list:
                    filtered_indices.append(i)
                    filtered_code_ids.append(code_id)

            indices_to_search = filtered_indices
            code_ids_to_search = filtered_code_ids

        if not code_ids_to_search:
            return JsonResponse({'status': 'error', 'message': 'No hay códigos de cierre para la aplicación seleccionada.'}, status=404)

        filtered_tfidf_matrix = tfidf_matrix[indices_to_search]
        
        # 1. Vectorizar la nueva descripción
        normalized_description = normalizar_texto(description)
        description_vector = vectorizer.transform([normalized_description])

        # 2. Calcular la similitud del coseno
        cosine_similarities = cosine_similarity(
            description_vector, filtered_tfidf_matrix).flatten()

        if cosine_similarities.size == 0:
            return JsonResponse({'status': 'error', 'message': 'Error al calcular la similitud.'}, status=500)

        # 3. Encontrar los Top 3 más similares
        # Ordenamos los índices de mayor a menor similitud
        # argsort devuelve índices ascendentes, tomamos los últimos (mayores) e invertimos
        top_k = min(3, len(cosine_similarities))
        top_indices_local = cosine_similarities.argsort()[-top_k:][::-1]
        
        sugerencias_response = []
        
        for idx in top_indices_local:
            score = cosine_similarities[idx]
            predicted_code_id = code_ids_to_search[idx]
            
            try:
                suggested_code = CodigoCierre.objects.get(pk=predicted_code_id)
                
                # Definir acción y mensaje por cada item
                if score >= SIMILARITY_THRESHOLD:
                    accion = 'use_suggestion'
                    msg = "Alta coincidencia"
                else:
                    accion = 'review'
                    msg = "Coincidencia baja"

                sugerencias_response.append({
                    'id': suggested_code.id,
                    'codigo_cierre': suggested_code.cod_cierre,
                    'descripcion': suggested_code.desc_cod_cierre,
                    'confianza': f"{score:.2%}",
                    'raw_score': float(score),
                    'accion_recomendada': accion,
                    'mensaje': msg
                })
            except CodigoCierre.DoesNotExist:
                continue

        logger.info(f"Enviando {len(sugerencias_response)} sugerencias.")
        return JsonResponse({'status': 'success', 'sugerencias': sugerencias_response})

    except Exception as e:
        logger.error(
            f"Error inesperado en recommend_closure_code_view: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Ocurrió un error inesperado al procesar la solicitud.'}, status=500)
