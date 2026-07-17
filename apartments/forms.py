from django import forms

from .models import Appartement, PeriodeVacances, Photo


class RechercheDisponibiliteForm(forms.Form):
    date_debut = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_fin = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        debut, fin = data.get('date_debut'), data.get('date_fin')
        if bool(debut) != bool(fin):
            raise forms.ValidationError("Saisissez les deux dates.")
        if debut and fin and fin <= debut:
            raise forms.ValidationError("La date de fin doit être postérieure à la date de début.")
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
