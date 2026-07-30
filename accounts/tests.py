from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.test import TestCase, override_settings
from django.urls import reverse

from .adapters import GoogleAccountAdapter
from .models import Utilisateur


GOOGLE_PROVIDER_SETTINGS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
        'EMAIL_AUTHENTICATION': True,
        'EMAIL_AUTHENTICATION_AUTO_CONNECT': True,
        'APPS': [{
            'client_id': 'client-google-de-test.apps.googleusercontent.com',
            'secret': 'secret-google-de-test',
            'key': '',
        }],
    },
}


@override_settings(
    GOOGLE_OAUTH_CONFIGURED=True,
    SOCIALACCOUNT_PROVIDERS=GOOGLE_PROVIDER_SETTINGS,
)
class InscriptionTests(TestCase):
    def test_pages_authentification_affichent_google(self):
        connexion = self.client.get(reverse('accounts:connexion'))
        inscription = self.client.get(reverse('accounts:inscription'))
        self.assertContains(connexion, 'Continuer avec Google')
        self.assertContains(inscription, 'S’inscrire avec Google')

    def test_bouton_google_demarre_oauth_et_callback_existe(self):
        response = self.client.post(reverse('google_login'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith('https://accounts.google.com/'))
        self.assertEqual(
            reverse('google_callback'),
            '/accounts/google/login/callback/',
        )

    def test_connexion_google_conserve_la_destination_demandee(self):
        destination = reverse('reservations:mes_reservations')
        response = self.client.get(
            reverse('accounts:connexion'),
            {'next': destination},
        )

        self.assertContains(
            response,
            f'<input type="hidden" name="next" value="{destination}">',
            html=True,
        )

    def test_adaptateur_google_remplit_un_nouveau_client(self):
        sociallogin = SocialLogin(
            user=Utilisateur(),
            account=SocialAccount(
                provider='google',
                uid='google-123',
                extra_data={
                    'email': 'client.google@example.com',
                    'given_name': 'Sara',
                    'family_name': 'Amrani',
                },
            ),
        )

        utilisateur = GoogleAccountAdapter().populate_user(
            request=None,
            sociallogin=sociallogin,
            data={'email': 'client.google@example.com'},
        )

        self.assertEqual(utilisateur.email, 'client.google@example.com')
        self.assertEqual(utilisateur.prenom, 'Sara')
        self.assertEqual(utilisateur.nom, 'Amrani')
        self.assertEqual(utilisateur.role, Utilisateur.CLIENT_REGULIER)

    def test_inscription_connecte_le_client(self):
        response = self.client.post(reverse('accounts:inscription'), {
            'role': Utilisateur.CLIENT_REGULIER, 'email': 'nouveau@example.com',
            'nom': 'Nouveau', 'prenom': 'Client', 'telephone': '', 'matricule': '',
            'password1': 'Mot-de-passe-tres-solide-2027', 'password2': 'Mot-de-passe-tres-solide-2027',
        })
        self.assertRedirects(response, reverse('reservations:mes_reservations'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_matricule_obligatoire_pour_enseignant(self):
        response = self.client.post(reverse('accounts:inscription'), {
            'role': Utilisateur.ENSEIGNANT, 'email': 'prof@example.com', 'nom': 'Prof', 'prenom': 'Test',
            'password1': 'Mot-de-passe-tres-solide-2027', 'password2': 'Mot-de-passe-tres-solide-2027',
        })
        self.assertContains(response, 'matricule est obligatoire')
