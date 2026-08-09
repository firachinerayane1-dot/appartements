from datetime import date, timedelta
import secrets
import string

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone


def generer_numero_reservation():
    """Génère un numéro au format aaAA00000, par exemple waZT74985."""
    lettres_minuscules = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(2))
    lettres_majuscules = ''.join(secrets.choice(string.ascii_uppercase) for _ in range(2))
    chiffres = ''.join(secrets.choice(string.digits) for _ in range(5))
    return f'{lettres_minuscules}{lettres_majuscules}{chiffres}'


class Reservation(models.Model):
    DELAI_PAIEMENT = timedelta(hours=24)
    MAX_NUITS_FM6_PAR_RESERVATION = 5
    MAX_NUITS_FM6_PAR_AN = 10
    MESSAGE_CHEVAUCHEMENT_ADHERENT = (
        "Cet adhérent possède déjà une réservation pendant cette période."
    )
    MESSAGE_DUREE_FM6 = "Une réservation FM6 est limitée à 5 nuits."
    MESSAGE_QUOTA_ANNUEL_FM6 = (
        "Ce client FM6 dépasserait son quota de 10 nuits pour l'année {annee}."
    )

    EN_ATTENTE = 'EN_ATTENTE'
    CONFIRMEE = 'CONFIRMEE'
    ANNULEE = 'ANNULEE'
    TERMINEE = 'TERMINEE'
    REJETEE = 'REJETEE'
    EXPIREE = 'EXPIREE'
    STATUT_CHOICES = [
        (EN_ATTENTE, 'En attente'),
        (CONFIRMEE, 'Confirmée'),
        (ANNULEE, 'Annulée'),
        (TERMINEE, 'Terminée'),
        (REJETEE, 'Rejetée'),
        (EXPIREE, 'Expirée'),
    ]

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reservations')
    appartement = models.ForeignKey('apartments.Appartement', on_delete=models.PROTECT, related_name='reservations')
    date_debut = models.DateField()
    date_fin = models.DateField()
    date_reservation = models.DateTimeField(auto_now_add=True)
    politiques_acceptees_le = models.DateTimeField(null=True, blank=True, editable=False)
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
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin <= self.date_debut:
            raise ValidationError({'date_fin': "La date de fin doit être postérieure à la date de début."})
        if self.client_id and self.client.est_administrateur():
            raise ValidationError({'client': "Un administrateur ne peut pas effectuer de réservation."})
        if self._bloque_une_periode() and self.reservations_adherent_en_conflit().exists():
            raise ValidationError(self.MESSAGE_CHEVAUCHEMENT_ADHERENT)
        if self._compte_dans_quota_fm6():
            if self.get_duree() > self.MAX_NUITS_FM6_PAR_RESERVATION:
                raise ValidationError(self.MESSAGE_DUREE_FM6)
            self._valider_quota_annuel_fm6()

    def _bloque_une_periode(self):
        # Le matricule représente l'adhésion FM6 : la limitation personnelle
        # ne s'applique donc pas aux clients réguliers.
        if not self.client_id or not self.client.est_client_fm6():
            return False
        if self.statut == self.CONFIRMEE:
            return True
        if self.statut != self.EN_ATTENTE:
            return False
        return not self.date_reservation or self.date_reservation > timezone.now() - self.DELAI_PAIEMENT

    def reservations_adherent_en_conflit(self):
        """Réservations actives du même adhérent sur une période semi-ouverte."""
        if not self.client_id or not self.date_debut or not self.date_fin:
            return type(self).objects.none()

        limite_paiement = timezone.now() - self.DELAI_PAIEMENT
        conflits = type(self).objects.filter(
            Q(statut=self.CONFIRMEE)
            | Q(statut=self.EN_ATTENTE, date_reservation__gt=limite_paiement),
            client_id=self.client_id,
            date_debut__lt=self.date_fin,
            date_fin__gt=self.date_debut,
        )
        if self.pk:
            conflits = conflits.exclude(pk=self.pk)
        return conflits

    def _compte_dans_quota_fm6(self):
        if not self.client_id or not self.client.est_client_fm6():
            return False
        if self.statut in (self.CONFIRMEE, self.TERMINEE):
            return True
        if self.statut != self.EN_ATTENTE:
            return False
        return not self.date_reservation or self.date_reservation > timezone.now() - self.DELAI_PAIEMENT

    def _valider_quota_annuel_fm6(self):
        """Impute chaque nuit FM6 à son année civile, départ exclu."""
        derniere_nuit = self.date_fin - timedelta(days=1)
        limite_paiement = timezone.now() - self.DELAI_PAIEMENT

        for annee in range(self.date_debut.year, derniere_nuit.year + 1):
            debut_annee = date(annee, 1, 1)
            fin_annee = date(annee + 1, 1, 1)
            nuits_nouvelles = (
                min(self.date_fin, fin_annee) - max(self.date_debut, debut_annee)
            ).days
            reservations = type(self).objects.filter(
                Q(statut__in=(self.CONFIRMEE, self.TERMINEE))
                | Q(statut=self.EN_ATTENTE, date_reservation__gt=limite_paiement),
                client_id=self.client_id,
                date_debut__lt=fin_annee,
                date_fin__gt=debut_annee,
            )
            if self.pk:
                reservations = reservations.exclude(pk=self.pk)

            nuits_existantes = sum(
                (min(reservation.date_fin, fin_annee) - max(reservation.date_debut, debut_annee)).days
                for reservation in reservations.only('date_debut', 'date_fin')
            )
            if nuits_existantes + nuits_nouvelles > self.MAX_NUITS_FM6_PAR_AN:
                raise ValidationError(self.MESSAGE_QUOTA_ANNUEL_FM6.format(annee=annee))

    def get_duree(self):
        return (self.date_fin - self.date_debut).days

    @property
    def date_expiration(self):
        if not self.date_reservation:
            return None
        return self.date_reservation + self.DELAI_PAIEMENT

    def est_expiree(self):
        return (
            self.statut == self.EN_ATTENTE
            and self.date_expiration is not None
            and timezone.now() >= self.date_expiration
        )

    def expirer_si_necessaire(self):
        if self.est_expiree():
            self.statut = self.EXPIREE
            self.save(update_fields=('statut',))
            return True
        return self.statut == self.EXPIREE

    @classmethod
    def expirer_en_attente(cls):
        limite = timezone.now() - cls.DELAI_PAIEMENT
        return cls.objects.filter(
            statut=cls.EN_ATTENTE,
            date_reservation__lte=limite,
        ).update(statut=cls.EXPIREE)

    def accepter_politiques(self):
        if self.expirer_si_necessaire():
            raise ValidationError("Le délai de paiement de 24 heures est expiré.")
        if self.statut != self.EN_ATTENTE:
            raise ValidationError("Cette réservation ne peut plus être payée.")
        if not self.politiques_acceptees_le:
            self.politiques_acceptees_le = timezone.now()
            self.save(update_fields=('politiques_acceptees_le',))
        return self

    def envoyer_email_politiques(self, lien_politiques):
        contexte = {
            'reservation': self,
            'lien_politiques': lien_politiques,
            'marque': settings.RAHAL_STAY_NAME,
        }
        send_mail(
            subject=f'Politiques de votre réservation {self.numero_reservation}',
            message=render_to_string('reservations/emails/politiques.txt', contexte),
            from_email=None,
            recipient_list=[self.client.email],
            html_message=render_to_string('reservations/emails/politiques.html', contexte),
        )

    def confirmer(self):
        if self.expirer_si_necessaire():
            raise ValidationError("Le délai de paiement de 24 heures est expiré.")
        if self.statut != self.EN_ATTENTE:
            raise ValidationError("Seule une réservation en attente peut être confirmée.")
        self.statut = self.CONFIRMEE
        self.save(update_fields=('statut',))
        return self

    def annuler(self):
        from payments.models import Paiement
        paiement_effectue = (
            self.pk
            and Paiement.objects.filter(reservation=self, statut=Paiement.PAYE).exists()
        )
        if self.statut == self.CONFIRMEE or paiement_effectue:
            raise ValidationError(
                "Une réservation payée ne peut pas être annulée et son tarif n'est pas remboursable."
            )
        if self.statut in (self.ANNULEE, self.TERMINEE, self.REJETEE, self.EXPIREE):
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
        if self.expirer_si_necessaire():
            raise ValidationError("Le délai de paiement de 24 heures est expiré.")
        if self.statut != self.EN_ATTENTE:
            raise ValidationError("Le paiement exige une réservation en attente.")
        from payments.models import Paiement
        if not self.politiques_acceptees_le:
            raise ValidationError("Vous devez lire et accepter les politiques avant le paiement.")
        if methode != Paiement.CARTE:
            raise ValidationError("Le paiement est disponible uniquement par carte bancaire.")
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
