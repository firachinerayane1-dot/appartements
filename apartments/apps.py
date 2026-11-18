from django.apps import AppConfig


class ApartmentsConfig(AppConfig):
    name = 'apartments'

    def ready(self):
        from django.db.models.signals import post_save, post_delete
        from .models import Appartement, Photo, PeriodeVacances
        from .cache import invalider_catalogue
        for model in (Appartement, Photo, PeriodeVacances):
            for signal in (post_save, post_delete):
                signal.connect(invalider_catalogue, sender=model,
                               dispatch_uid=f'catalogue-{model.__name__}-{id(signal)}')
