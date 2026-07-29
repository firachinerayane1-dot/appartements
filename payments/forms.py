import re
from django import forms


class PaiementForm(forms.Form):
    numero_carte = forms.CharField(max_length=19, label='Numéro de carte factice')
    expiration = forms.CharField(max_length=5, help_text='MM/AA')
    cvv = forms.CharField(max_length=4)

    def clean(self):
        data = super().clean()
        numero = re.sub(r'\s+', '', data.get('numero_carte', ''))
        if not re.fullmatch(r'\d{16}', numero):
            self.add_error('numero_carte', "Saisissez 16 chiffres.")
        if not re.fullmatch(r'(0[1-9]|1[0-2])/\d{2}', data.get('expiration', '')):
            self.add_error('expiration', "Format attendu : MM/AA.")
        if not re.fullmatch(r'\d{3,4}', data.get('cvv', '')):
            self.add_error('cvv', "Saisissez 3 ou 4 chiffres.")
        return data
