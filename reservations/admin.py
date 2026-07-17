from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'appartement', 'date_debut', 'date_fin', 'statut', 'montant_total')
    list_filter = ('statut', 'date_debut', 'date_fin', 'appartement')
    search_fields = ('client__email', 'appartement__titre')
    date_hierarchy = 'date_debut'
