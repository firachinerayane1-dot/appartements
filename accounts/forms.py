from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Utilisateur
from django.contrib.auth.forms import AuthenticationForm


class InscriptionForm(UserCreationForm):
    # On redéfinit "role" ici avec une liste de choix restreinte,
    # sans le "Administrateur" du modèle — impossible de le sélectionner,
    # même en trafiquant la requête manuellement.
    role = forms.ChoiceField(
        choices=[
            (Utilisateur.CLIENT_REGULIER, 'Client Régulier'),
            (Utilisateur.ENSEIGNANT, 'Enseignant'),
        ],
        label="Vous êtes",
    )

    class Meta:
        model = Utilisateur
        fields = ('role', 'email', 'nom', 'prenom', 'telephone', 'matricule')

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        matricule = cleaned_data.get('matricule')

        if role == Utilisateur.ENSEIGNANT and not matricule:
            self.add_error('matricule', "Le matricule est obligatoire pour les enseignants.")

        return cleaned_data


class ConnexionForm(AuthenticationForm):
    username = forms.CharField(label="Email")