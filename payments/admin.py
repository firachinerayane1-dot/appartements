from django.contrib import admin
from .models import Paiement


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'montant', 'methode', 'statut', 'date_paiement')
    list_filter = ('statut', 'methode', 'date_paiement')
    search_fields = ('reservation__client__email',)
