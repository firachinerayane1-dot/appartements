from django import forms
from django.utils import timezone

from .models import Appartement, PeriodeVacances, Photo


class RechercheDisponibiliteForm(forms.Form):
    date_debut = forms.DateField(
        label="Date d'arrivée",
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    date_fin = forms.DateField(
        label='Date de départ',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        date_minimale = timezone.localdate().isoformat()
        self.fields['date_debut'].widget.attrs['min'] = date_minimale
        self.fields['date_fin'].widget.attrs['min'] = date_minimale

    def clean(self):
        data = super().clean()
        debut, fin = data.get('date_debut'), data.get('date_fin')
        if debut and debut < timezone.localdate():
            self.add_error('date_debut', "La date d'arrivée ne peut pas être passée.")
        if debut and fin and fin <= debut:
            self.add_error('date_fin', "La date de départ doit être postérieure à la date d'arrivée.")
        return data


class AppartementForm(forms.ModelForm):
    class Meta:
        model = Appartement
        fields = ('titre', 'description', 'prix_par_nuit', 'capacite', 'disponible')


class PeriodeVacancesForm(forms.ModelForm):
    class Meta:
        model = PeriodeVacances
        fields = ('appartement', 'date_debut', 'date_fin', 'libelle')
        widgets = {'date_debut': forms.DateInput(attrs={'type': 'date'}), 'date_fin': forms.DateInput(attrs={'type': 'date'})}


class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ('image', 'legende', 'principale')
