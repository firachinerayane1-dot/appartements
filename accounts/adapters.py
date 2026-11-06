from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse
from urllib.parse import urlencode

from .models import Utilisateur
from .redirects import destination_sure


class GoogleAccountAdapter(DefaultSocialAccountAdapter):
    """Adapte le profil Google aux champs français du modèle utilisateur."""

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        if sociallogin.account.provider == 'google':
            destination = destination_sure(request, sociallogin.state.get('next'))
            sociallogin.state['next'] = (
                reverse('accounts:completer_adherent') + '?' + urlencode({'next': destination})
            )
        return user

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        extra = sociallogin.account.extra_data or {}
        email = data.get('email') or extra.get('email') or ''

        user.prenom = (
            data.get('first_name')
            or extra.get('given_name')
            or email.split('@')[0]
            or 'Client'
        )
        user.nom = data.get('last_name') or extra.get('family_name') or 'Google'
        user.role = Utilisateur.CLIENT_REGULIER
        return user
