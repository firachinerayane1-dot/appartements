from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone


class Paiement(models.Model):
    CARTE = 'CARTE'  # Historique uniquement.
    VIREMENT = 'VIREMENT'
    METHODES = [(VIREMENT, 'Virement bancaire'), (CARTE, 'Carte bancaire (historique)')]
    EN_ATTENTE = 'EN_ATTENTE'
    PAYE = 'PAYE'
    ECHEC = 'ECHEC'
    STATUTS = [(EN_ATTENTE, 'En attente'), (PAYE, 'Payé'), (ECHEC, 'Échec')]

    reservation = models.OneToOneField('reservations.Reservation', on_delete=models.CASCADE, related_name='paiement')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    methode = models.CharField(max_length=20, choices=METHODES)
    statut = models.CharField(max_length=20, choices=STATUTS, default=EN_ATTENTE)
    date_paiement = models.DateTimeField(null=True, blank=True)
    valide_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, editable=False, related_name='paiements_valides')
    reference_virement = models.CharField(max_length=140, blank=True)

    class Meta:
        ordering = ('-date_paiement', '-pk')

    def __str__(self):
        return f"Paiement #{self.pk} — {self.get_statut_display()}"

    @transaction.atomic
    def effectuer(self, administrateur=None, reference=''):
        from reservations.models import Reservation
        from services.reservation_services import _verrouiller_client, _verrouiller_appartements
        if not administrateur or not administrateur.est_administrateur():
            raise PermissionDenied("Seul un administrateur peut valider le virement.")
        reservation = Reservation.objects.get(pk=self.reservation_id)
        _verrouiller_client(reservation.client)
        appartement = _verrouiller_appartements(reservation.appartement_id)[reservation.appartement_id]
        reservation = Reservation.objects.select_for_update().get(pk=self.reservation_id)
        paiement = type(self).objects.select_for_update().get(pk=self.pk)
        self.validation_nouvelle = False
        if paiement.statut == self.PAYE:
            self.refresh_from_db()
            return self
        if reservation.est_expiree():
            raise ValidationError("Le délai de validation de 24 heures est expiré. Contactez le client pour traiter le virement reçu.")
        if reservation.statut != Reservation.EN_ATTENTE:
            raise ValidationError("La réservation doit être en attente.")
        if not reservation.politiques_acceptees_le:
            raise ValidationError("Les politiques doivent être acceptées avant le paiement.")
        if paiement.methode != self.VIREMENT:
            raise ValidationError("Seul un virement bancaire peut être validé.")
        if not reference.strip():
            raise ValidationError("Indiquez la référence du virement vérifié.")
        if paiement.montant != reservation.montant_total:
            raise ValidationError("Le montant du paiement ne correspond pas à la réservation.")
        if not appartement.is_disponible(reservation.date_debut, reservation.date_fin, exclude_reservation=reservation.pk):
            raise ValidationError("Ces dates ne sont plus disponibles. Contactez le client.")
        reservation.statut = Reservation.CONFIRMEE
        reservation.full_clean()
        reservation.save(update_fields=('statut',))
        paiement.statut = self.PAYE
        paiement.date_paiement = timezone.now()
        paiement.valide_par = administrateur
        paiement.reference_virement = reference.strip()
        paiement.full_clean()
        paiement.save(update_fields=('statut', 'date_paiement', 'valide_par', 'reference_virement'))
        self.refresh_from_db()
        self.validation_nouvelle = True
        return self

    def get_recu(self):
        return {
            'numero': self.pk, 'reservation': self.reservation.numero_reservation,
            'client': str(self.reservation.client), 'montant': self.montant,
            'methode': self.get_methode_display(), 'date': self.date_paiement,
            'référence du virement': self.reference_virement,
        }
