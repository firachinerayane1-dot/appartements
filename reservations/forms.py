from django import forms
from django.utils import timezone


class ReservationForm(forms.Form):
    date_debut = forms.DateField(
        label="Date d'arrivée",
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    date_fin = forms.DateField(
        label='Date de départ',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def clean(self):
        data = super().clean()
        debut, fin = data.get('date_debut'), data.get('date_fin')
        if debut and debut < timezone.localdate():
            self.add_error('date_debut', "La date de début ne peut pas être passée.")
        if debut and fin and fin <= debut:
            self.add_error('date_fin', "La date de fin doit être postérieure à la date de début.")
        return data


class FiltreReservationAdminForm(forms.Form):
    statut = forms.ChoiceField(required=False, choices=[('', 'Tous les statuts')])
    appartement = forms.ModelChoiceField(required=False, queryset=None)
    date_debut = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_fin = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        from apartments.models import Appartement
        from .models import Reservation
        super().__init__(*args, **kwargs)
        self.fields['statut'].choices += Reservation.STATUT_CHOICES
        self.fields['appartement'].queryset = Appartement.objects.all()
