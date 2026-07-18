import re
from django import forms
from .models import Paiement


class PaiementForm(forms.Form):
    methode = forms.ChoiceField(choices=Paiement.METHODES)
    numero_carte = forms.CharField(required=False, max_length=19, label='Numéro de carte factice')
    expiration = forms.CharField(required=False, max_length=5, help_text='MM/AA')
    cvv = forms.CharField(required=False, max_length=4)

    def clean(self):
        data = super().clean()
        if data.get('methode') == Paiement.CARTE:
            numero = re.sub(r'\s+', '', data.get('numero_carte', ''))
            if not re.fullmatch(r'\d{16}', numero):
                self.add_error('numero_carte', "Saisissez 16 chiffres.")
            if not re.fullmatch(r'(0[1-9]|1[0-2])/\d{2}', data.get('expiration', '')):
                self.add_error('expiration', "Format attendu : MM/AA.")
            if not re.fullmatch(r'\d{3,4}', data.get('cvv', '')):
                self.add_error('cvv', "Saisissez 3 ou 4 chiffres.")
        return data
