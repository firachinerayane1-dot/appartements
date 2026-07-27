from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('numero_reservation', 'client', 'appartement', 'date_debut', 'date_fin', 'statut', 'montant_total')
    list_filter = ('statut', 'date_debut', 'date_fin', 'appartement')
    search_fields = ('numero_reservation', 'client__email', 'appartement__titre')
    readonly_fields = ('numero_reservation',)
    date_hierarchy = 'date_debut'
