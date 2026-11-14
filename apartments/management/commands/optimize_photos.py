from django.core.management.base import BaseCommand
from apartments.models import Photo


class Command(BaseCommand):
    help = 'Génère les variantes WebP manquantes des photos existantes, sans supprimer les originaux.'

    def handle(self, *args, **options):
        count = 0
        for photo in Photo.objects.iterator():
            if photo.image and not photo.variantes:
                photo.optimiser_image()
                photo.save(update_fields=['variantes'])
                count += 1
        self.stdout.write(self.style.SUCCESS(f'{count} photos optimisées.'))
