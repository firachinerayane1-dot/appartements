import secrets
import string

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q


def generer_numero_reservation():
    """Génère un numéro au format aaAA00000, par exemple waZT74985."""
    lettres_minuscules = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(2))
    lettres_majuscules = ''.join(secrets.choice(string.ascii_uppercase) for _ in range(2))
    chiffres = ''.join(secrets.choice(string.digits) for _ in range(5))
    return f'{lettres_minuscules}{lettres_majuscules}{chiffres}'


class Reservation(models.Model):
    EN_ATTENTE = 'EN_ATTENTE'
    CONFIRMEE = 'CONFIRMEE'
    ANNULEE = 'ANNULEE'
    TERMINEE = 'TERMINEE'
    REJETEE = 'REJETEE'
    STATUT_CHOICES = [
        (EN_ATTENTE, 'En attente'),
        (CONFIRMEE, 'Confirmée'),
        (ANNULEE, 'Annulée'),
        (TERMINEE, 'Terminée'),
        (REJETEE, 'Rejetée'),
    ]

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reservations')
    appartement = models.ForeignKey('apartments.Appartement', on_delete=models.PROTECT, related_name='reservations')
    date_debut = models.DateField()
    date_fin = models.DateField()
    date_reservation = models.DateTimeField(auto_now_add=True)
    numero_reservation = models.CharField(
        max_length=9,
        unique=True,
        default=generer_numero_reservation,
        editable=False,
        validators=[
            RegexValidator(
                regex=r'^[a-z]{2}[A-Z]{2}\d{5}$',
                message='Le numéro de réservation doit contenir 2 lettres minuscules, '
                        '2 lettres majuscules et 5 chiffres.',
            ),
        ],
    )
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=EN_ATTENTE)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ('-date_reservation',)
        constraints = [models.CheckConstraint(condition=Q(date_fin__gt=models.F('date_debut')), name='reservation_dates_valides')]

    def __str__(self):
        return f"{self.numero_reservation} — {self.client} — {self.appartement} ({self.date_debut})"

    def clean(self):
        if self.date_debut and self.date_fin and self.date_fin <= self.date_debut:
            raise ValidationError({'date_fin': "La date de fin doit être postérieure à la date de début."})
        if self.client_id and self.client.est_administrateur():
            raise ValidationError({'client': "Un administrateur ne peut pas effectuer de réservation."})

    def get_duree(self):
        return (self.date_fin - self.date_debut).days

    def confirmer(self):
        if self.statut != self.EN_ATTENTE:
            raise ValidationError("Seule une réservation en attente peut être confirmée.")
        self.statut = self.CONFIRMEE
        self.save(update_fields=('statut',))
        return self

    def annuler(self):
        if self.statut in (self.ANNULEE, self.TERMINEE):
            return self
        self.statut = self.ANNULEE
        self.save(update_fields=('statut',))
        from notifications.models import Notification
        Notification.objects.create(
            client=self.client,
            message=f"Votre réservation de {self.appartement} du {self.date_debut:%d/%m/%Y} au {self.date_fin:%d/%m/%Y} a été annulée.",
        ).envoyer()
        return self

    def generer_paiement(self, methode):
        if self.statut != self.EN_ATTENTE:
            raise ValidationError("Le paiement exige une réservation en attente.")
        from payments.models import Paiement
        paiement, _ = Paiement.objects.get_or_create(
            reservation=self,
            defaults={'montant': self.montant_total, 'methode': methode},
        )
        if paiement.statut == Paiement.PAYE:
            raise ValidationError("Cette réservation est déjà payée.")
        paiement.methode = methode
        paiement.montant = self.montant_total
        paiement.save()
        return paiement

    def generer_recap(self):
        return {
            'numero': self.numero_reservation,
            'client': str(self.client),
            'appartement': str(self.appartement),
            'date_debut': self.date_debut,
            'date_fin': self.date_fin,
            'duree': self.get_duree(),
            'montant_total': self.montant_total,
            'statut': self.get_statut_display(),
        }
