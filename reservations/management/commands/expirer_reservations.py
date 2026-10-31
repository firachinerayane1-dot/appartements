from django.core.management.base import BaseCommand

from reservations.models import Reservation


class Command(BaseCommand):
    help = (
        "Expire les réservations non validées depuis 24 heures et envoie une "
        "notification interne aux clients concernés."
    )

    def handle(self, *args, **options):
        nombre = Reservation.expirer_en_attente()
        self.stdout.write(
            self.style.SUCCESS(
                f"{nombre} réservation(s) expirée(s) et client(s) notifié(s)."
            )
        )
