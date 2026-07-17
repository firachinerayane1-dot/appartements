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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        attributs = {
            'email': {'placeholder': 'vous@exemple.com', 'autocomplete': 'email'},
            'nom': {'placeholder': 'Votre nom', 'autocomplete': 'family-name'},
            'prenom': {'placeholder': 'Votre prénom', 'autocomplete': 'given-name'},
            'telephone': {'placeholder': '+212 6 00 00 00 00', 'autocomplete': 'tel'},
            'matricule': {'placeholder': 'Votre matricule'},
            'password1': {'placeholder': 'Au moins 8 caractères', 'autocomplete': 'new-password'},
            'password2': {'placeholder': 'Confirmez le mot de passe', 'autocomplete': 'new-password'},
        }
        for nom, field in self.fields.items():
            field.widget.attrs.update(attributs.get(nom, {}))
            field.widget.attrs['class'] = 'auth-input'

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        matricule = cleaned_data.get('matricule')

        if role == Utilisateur.ENSEIGNANT and not matricule:
            self.add_error('matricule', "Le matricule est obligatoire pour les enseignants.")

        return cleaned_data

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        if utilisateur.role != Utilisateur.ENSEIGNANT:
            utilisateur.matricule = None
        if commit:
            utilisateur.save()
        return utilisateur


class ConnexionForm(AuthenticationForm):
    username = forms.CharField(label="Email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'auth-input', 'placeholder': 'vous@exemple.com', 'autocomplete': 'email',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'auth-input', 'placeholder': 'Votre mot de passe', 'autocomplete': 'current-password',
        })


class ProfilForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ('email', 'nom', 'prenom', 'telephone', 'matricule')

    def clean_matricule(self):
        matricule = self.cleaned_data.get('matricule')
        if self.instance.est_enseignant() and not matricule:
            raise forms.ValidationError("Le matricule est obligatoire pour un enseignant.")
        return matricule
