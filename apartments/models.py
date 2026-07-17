from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Appartement(models.Model):
    titre = models.CharField(max_length=150)
    description = models.TextField()
    prix_par_nuit = models.DecimalField(max_digits=10, decimal_places=2)
    capacite = models.PositiveIntegerField(default=1)
    disponible = models.BooleanField(default=True)

    class Meta:
        ordering = ('titre',)

    def __str__(self):
        return self.titre

    def clean(self):
        if self.prix_par_nuit is not None and self.prix_par_nuit <= 0:
            raise ValidationError({'prix_par_nuit': "Le prix doit être strictement positif."})
        if self.capacite is not None and self.capacite < 1:
            raise ValidationError({'capacite': "La capacité doit être d'au moins une personne."})

    def is_disponible(self, date_debut, date_fin, exclude_reservation=None):
        if not self.disponible or not date_debut or not date_fin or date_fin <= date_debut:
            return False
        if not hasattr(self, 'reservations'):
            return True
        conflits = self.reservations.filter(
            statut__in=('EN_ATTENTE', 'CONFIRMEE'),
            date_debut__lt=date_fin,
            date_fin__gt=date_debut,
        )
        if exclude_reservation:
            conflits = conflits.exclude(pk=exclude_reservation)
        return not conflits.exists()

    def calculer_prix(self, date_debut, date_fin, client=None):
        nuits = (date_fin - date_debut).days
        if nuits <= 0:
            raise ValidationError("La date de fin doit être postérieure à la date de début.")
        total = self.prix_par_nuit * nuits
        reduction = Decimal(str(client.taux_reduction())) if client else Decimal('0')
        return (total * (Decimal('1') - reduction)).quantize(Decimal('0.01'))


class PeriodeVacances(models.Model):
    appartement = models.ForeignKey(Appartement, on_delete=models.CASCADE, related_name='periodes_vacances')
    date_debut = models.DateField()
    date_fin = models.DateField()
    libelle = models.CharField(max_length=150)

    class Meta:
        ordering = ('date_debut',)
        verbose_name_plural = 'périodes de vacances'
        constraints = [models.CheckConstraint(condition=Q(date_fin__gt=models.F('date_debut')), name='vacances_dates_valides')]

    def __str__(self):
        return f"{self.libelle} — {self.appartement}"

    def clean(self):
        if self.date_debut and self.date_fin and self.date_fin <= self.date_debut:
            raise ValidationError({'date_fin': "La date de fin doit être postérieure à la date de début."})

    def is_active(self, date=None):
        date = date or timezone.localdate()
        return self.date_debut <= date < self.date_fin

    def chevauche(self, date_debut, date_fin):
        return self.date_debut < date_fin and self.date_fin > date_debut


class Photo(models.Model):
    appartement = models.ForeignKey(Appartement, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='appartements/')
    legende = models.CharField(max_length=150, blank=True)
    principale = models.BooleanField(default=False)

    def __str__(self):
        return self.legende or f"Photo de {self.appartement}"
