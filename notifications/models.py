from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Notification(models.Model):
    INFORMATION = 'INFORMATION'
    EXPIRATION_RESERVATION = 'EXPIRATION_RESERVATION'
    CATEGORIES = [
        (INFORMATION, 'Information'),
        (EXPIRATION_RESERVATION, 'Expiration de réservation'),
    ]

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    reservation = models.ForeignKey(
        'reservations.Reservation',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
    )
    categorie = models.CharField(max_length=30, choices=CATEGORIES, default=INFORMATION)
    message = models.TextField()
    date_envoi = models.DateTimeField(null=True, blank=True)
    lue = models.BooleanField(default=False)

    class Meta:
        ordering = ('-date_envoi', '-pk')
        constraints = [
            models.UniqueConstraint(
                fields=('reservation', 'categorie'),
                condition=Q(
                    reservation__isnull=False,
                    categorie='EXPIRATION_RESERVATION',
                ),
                name='notification_expiration_reservation_unique',
            ),
        ]

    def __str__(self):
        return f"Notification pour {self.client}"

    def marquer_lue(self):
        if not self.lue:
            self.lue = True
            self.save(update_fields=('lue',))
        return self

    def envoyer(self):
        if not self.date_envoi:
            self.date_envoi = timezone.now()
            self.save(update_fields=('date_envoi',))
        return self
