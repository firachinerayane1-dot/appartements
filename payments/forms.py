from django import forms


class ValidationVirementForm(forms.Form):
    reference_virement = forms.CharField(max_length=140, label='Référence bancaire du virement')
    paiement_verifie = forms.BooleanField(label='J’ai vérifié la réception du montant total sur le compte bancaire.')
    client_contacte = forms.BooleanField(label='Le support a contacté le client et confirmé les informations du séjour.')


class FiltrePaiementForm(forms.Form):
    from .models import Paiement
    statut = forms.ChoiceField(required=False, choices=[('', 'Tous les statuts'), *Paiement.STATUTS])
    methode = forms.ChoiceField(label='Méthode', required=False, choices=[('', 'Toutes les méthodes'), *Paiement.METHODES])
    date = forms.DateField(label='Date de validation', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
