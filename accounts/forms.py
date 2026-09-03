from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from .models import Utilisateur
from django.contrib.auth.forms import AuthenticationForm


class InscriptionForm(UserCreationForm):
    # On redéfinit "role" ici avec une liste de choix restreinte,
    # sans le "Administrateur" du modèle — impossible de le sélectionner,
    # même en trafiquant la requête manuellement.
    role = forms.ChoiceField(
        choices=[
            (Utilisateur.CLIENT_REGULIER, 'Client Régulier'),
            (Utilisateur.CLIENT_FM6, 'Client FM6'),
        ],
        label="Vous êtes",
    )
    consentement_donnees = forms.BooleanField(
        required=True,
        label="J’ai lu et compris la politique de confidentialité.",
        error_messages={
            'required': "Vous devez lire et accepter la politique de confidentialité.",
        },
    )

    class Meta:
        model = Utilisateur
        fields = (
            'role', 'email', 'nom', 'prenom', 'telephone', 'matricule',
            'consentement_donnees',
        )

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
            field.widget.attrs['class'] = (
                'auth-checkbox-input'
                if isinstance(field.widget, forms.CheckboxInput)
                else 'auth-input'
            )

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        matricule = (cleaned_data.get('matricule') or '').strip() or None

        if role == Utilisateur.CLIENT_FM6 and not matricule:
            self.add_error('matricule', "Le matricule est obligatoire pour un client FM6.")
        if role != Utilisateur.CLIENT_FM6:
            matricule = None
        cleaned_data['matricule'] = matricule

        return cleaned_data

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        if utilisateur.role != Utilisateur.CLIENT_FM6:
            utilisateur.matricule = None
        utilisateur.consentement_donnees_le = timezone.now()
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
        matricule = (self.cleaned_data.get('matricule') or '').strip() or None
        if self.instance.est_client_fm6() and not matricule:
            raise forms.ValidationError("Le matricule est obligatoire pour un client FM6.")
        return matricule

    def save(self, commit=True):
        utilisateur = super().save(commit=False)
        if utilisateur.matricule and not utilisateur.est_administrateur():
            utilisateur.role = Utilisateur.CLIENT_FM6
        if commit:
            utilisateur.save()
            self.save_m2m()
        return utilisateur
