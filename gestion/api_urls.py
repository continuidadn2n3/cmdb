from django.urls import path
from .views import recommendations

app_name = 'gestion_api'

urlpatterns = [
    # Aquí van todas las URLs de tu API
    path('recommend-closure-code/', recommendations.recommend_closure_code_view,
         name='recommend_closure_code'),
    path('train-model/', recommendations.reentrenar_modelo_view,
         name='train_model'),
]
