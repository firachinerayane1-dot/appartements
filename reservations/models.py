from django.db import models
from django.conf import settings
# Create your models here.
class Reservation(models.Model):
    STATUT=[
        ("ANNULEE","annulée"),
        ("EN_ATTENTE","en attente")
        ("CONFIRMEE","confirmée"),
        ("TERMINEE","Terminée"),
        ("REJETEE","Rejetée"),
    ]
    TYPE = [
        ("STANDARD", "Standard"),
        ("REGULIER", "Client régulier"),
    ]
    #une reservation lier a un Utilisateur
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name="reservations")
    appartement = models.ForeignKey("apartments.appartement",on_delete=models.PROTECT,related_name="reservations")
    date_reservation = models.DateField(auto_now_add=True)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField()
    statut=models.CharField(choices=STATUT)
    remise_appliquee=models.DecimalField(max_digits=10,decimal_places=2)
    prix_total = models.DecimalField(max_digits=10, decimal_places=2)
    type_reservation= models.CharField(choices=TYPE)

    def __str__(self):
        return f"{self.utilisateur} - {self.appartement} - {self.date_reservation}"
