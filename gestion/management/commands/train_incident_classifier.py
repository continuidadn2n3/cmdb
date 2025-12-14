# gestion/management/commands/train_incident_classifier.py

from django.core.management.base import BaseCommand
from gestion.ml.incident_classifier import build_and_save_similarity_model


class Command(BaseCommand):
    help = 'Construye y guarda el modelo de similitud de texto para los Códigos de Cierre.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            'Iniciando la construcción del modelo de similitud...'))
        try:
            build_and_save_similarity_model()
            self.stdout.write(self.style.SUCCESS('¡Construcción completada!'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f'Ocurrió un error durante la construcción: {e}'))
