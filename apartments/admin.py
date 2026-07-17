from django.contrib import admin
from .models import Appartement, PeriodeVacances, Photo


class PeriodeVacancesInline(admin.TabularInline):
    model = PeriodeVacances
    extra = 0


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 0


@admin.register(Appartement)
class AppartementAdmin(admin.ModelAdmin):
    list_display = ('titre', 'prix_par_nuit', 'capacite', 'disponible')
    list_filter = ('disponible', 'capacite')
    search_fields = ('titre', 'description')
    inlines = (PeriodeVacancesInline, PhotoInline)


admin.site.register(PeriodeVacances)
admin.site.register(Photo)
