from django import forms


class PeriodeForm(forms.Form):
    date_debut = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_fin = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        debut, fin = data.get('date_debut'), data.get('date_fin')
        if bool(debut) != bool(fin):
            raise forms.ValidationError("Saisissez les deux bornes de la période.")
        if debut and fin and fin <= debut:
            raise forms.ValidationError("La date de fin doit être postérieure à la date de début.")
        return data
