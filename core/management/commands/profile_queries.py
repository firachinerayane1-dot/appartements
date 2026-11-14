"""Read-only timings and execution plans for the main list queries."""
from datetime import date, timedelta
from statistics import median
from time import perf_counter

from django.core.management.base import BaseCommand
from django.utils import timezone

from apartments.models import Appartement, Photo
from notifications.models import Notification
from reservations.models import Reservation


class Command(BaseCommand):
    help = 'Mesure les listes et affiche leurs plans EXPLAIN, sans modifier les données.'

    def add_arguments(self, parser):
        parser.add_argument('--client-id', type=int, required=True)
        parser.add_argument('--repeat', type=int, default=5)
        parser.add_argument('--date-debut', type=date.fromisoformat, default=timezone.localdate())
        parser.add_argument('--date-fin', type=date.fromisoformat)

    def handle(self, *args, **options):
        client_id = options['client_id']
        queries = {
            'reservations_client': Reservation.objects.filter(client_id=client_id)[:12],
            'reservations_admin': Reservation.objects.all()[:20],
            'reservations_attente': Reservation.objects.filter(statut=Reservation.EN_ATTENTE)[:20],
            'notifications': Notification.objects.filter(client_id=client_id)[:20],
            'notifications_non_lues': Notification.objects.filter(client_id=client_id, lue=False).order_by().values('pk'),
            'appartements': Appartement.objects.all()[:20],
        }
        appartement = Appartement.objects.order_by('pk').values_list('pk', flat=True).first()
        if appartement is not None:
            queries['disponibilite'] = Reservation.objects.filter(
                appartement_id=appartement, statut=Reservation.CONFIRMEE,
                date_fin__gt=options['date_debut'],
                date_debut__lt=options['date_fin'] or options['date_debut'] + timedelta(days=7),
            ).order_by().values('pk')[:1]
            queries['photos_carte'] = Photo.objects.filter(appartement_id=appartement).order_by('-principale', 'pk')[:3]
        for name, queryset in queries.items():
            times = []
            for _ in range(max(1, options['repeat'])):
                start = perf_counter()
                # A fresh clone avoids Django's result cache on every repetition.
                for _row in queryset.all().iterator(chunk_size=500):
                    pass
                times.append((perf_counter() - start) * 1000)
            self.stdout.write(f'{name}: median_ms={median(times):.3f} max_ms={max(times):.3f}')
            self.stdout.write(queryset.explain())
