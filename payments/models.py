from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class Paiement(models.Model):
    CARTE = 'CARTE'
    VIREMENT = 'VIREMENT'
    ESPECES = 'ESPECES'
    METHODES = [(CARTE, 'Carte'), (VIREMENT, 'Virement'), (ESPECES, 'Espèces')]
    EN_ATTENTE = 'EN_ATTENTE'
    PAYE = 'PAYE'
    ECHEC = 'ECHEC'
    STATUTS = [(EN_ATTENTE, 'En attente'), (PAYE, 'Payé'), (ECHEC, 'Échec')]

    reservation = models.OneToOneField('reservations.Reservation', on_delete=models.CASCADE, related_name='paiement')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    methode = models.CharField(max_length=20, choices=METHODES)
    statut = models.CharField(max_length=20, choices=STATUTS, default=EN_ATTENTE)
    date_paiement = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-date_paiement', '-pk')

    def __str__(self):
        return f"Paiement #{self.pk} — {self.get_statut_display()}"

    @transaction.atomic
    def effectuer(self):
        from reservations.models import Reservation
        reservation = Reservation.objects.select_for_update().get(pk=self.reservation_id)
        if self.statut == self.PAYE:
            return self
        if reservation.statut != Reservation.EN_ATTENTE:
            raise ValidationError("La réservation doit être en attente.")
        if self.montant != reservation.montant_total:
            raise ValidationError("Le montant du paiement ne correspond pas à la réservation.")
        self.statut = self.PAYE
        self.date_paiement = timezone.now()
        self.save(update_fields=('statut', 'date_paiement'))
        reservation.confirmer()
        return self

    def get_recu(self):
        return {
            'numero': self.pk,
            'reservation': self.reservation_id,
            'client': str(self.reservation.client),
            'montant': self.montant,
            'methode': self.get_methode_display(),
            'date': self.date_paiement,
        }
