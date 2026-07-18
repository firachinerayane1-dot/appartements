from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import Utilisateur


class GoogleAccountAdapter(DefaultSocialAccountAdapter):
    """Adapte le profil Google aux champs français du modèle utilisateur."""

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
