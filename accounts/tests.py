from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.db import IntegrityError, transaction
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

    def test_connexion_google_ignore_la_destination_et_revient_a_l_accueil(self):
        destination = reverse('reservations:mes_reservations')
        response = self.client.get(
            reverse('accounts:connexion'),
            {'next': destination},
        )

        self.assertNotContains(response, 'name="next"')

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
            'consentement_donnees': 'on',
        })
        self.assertRedirects(response, reverse('core:accueil'))
        self.assertIn('_auth_user_id', self.client.session)
        self.assertIsNotNone(
            Utilisateur.objects.get(email='nouveau@example.com').consentement_donnees_le
        )

    def test_consentement_aux_politiques_et_aux_donnees_est_obligatoire(self):
        response = self.client.post(reverse('accounts:inscription'), {
            'role': Utilisateur.CLIENT_REGULIER,
            'email': 'sans-consentement@example.com',
            'nom': 'Sans',
            'prenom': 'Consentement',
            'password1': 'Mot-de-passe-tres-solide-2027',
            'password2': 'Mot-de-passe-tres-solide-2027',
        })

        self.assertContains(response, 'Vous devez lire et accepter la politique de confidentialité')
        self.assertFalse(Utilisateur.objects.filter(email='sans-consentement@example.com').exists())

    def test_inscription_affiche_le_lien_vers_la_politique_de_confidentialite(self):
        response = self.client.get(reverse('accounts:inscription'))

        self.assertContains(response, 'J’ai lu et compris la')
        self.assertContains(response, reverse('core:politique_confidentialite'))

    def test_connexion_redirige_vers_accueil_meme_avec_next(self):
        utilisateur = Utilisateur.objects.create_user(
            email='client@example.com',
            password='mot-de-passe-solide',
            nom='Client',
            prenom='Test',
        )

        response = self.client.post(
            f"{reverse('accounts:connexion')}?next={reverse('reservations:mes_reservations')}",
            {'username': utilisateur.email, 'password': 'mot-de-passe-solide'},
        )

        self.assertRedirects(response, reverse('core:accueil'))

    def test_ajouter_un_matricule_transforme_le_client_en_client_fm6(self):
        utilisateur = Utilisateur.objects.create_user(
            email='profil@example.com',
            password='mot-de-passe-solide',
            nom='Profil',
            prenom='Client',
        )
        self.client.force_login(utilisateur)

        response = self.client.post(reverse('accounts:modifier_profil'), {
            'email': utilisateur.email,
            'nom': utilisateur.nom,
            'prenom': utilisateur.prenom,
            'telephone': '0600000000',
            'matricule': ' FONDATION-123 ',
        })

        self.assertRedirects(response, reverse('accounts:profil'))
        utilisateur.refresh_from_db()
        self.assertEqual(utilisateur.matricule, 'FONDATION-123')
        self.assertEqual(utilisateur.role, Utilisateur.CLIENT_FM6)
        self.assertEqual(utilisateur.get_role_display(), 'Client FM6')

    def test_matricule_obligatoire_pour_client_fm6(self):
        response = self.client.post(reverse('accounts:inscription'), {
            'role': Utilisateur.CLIENT_FM6, 'email': 'fm6@example.com', 'nom': 'FM6', 'prenom': 'Test',
            'password1': 'Mot-de-passe-tres-solide-2027', 'password2': 'Mot-de-passe-tres-solide-2027',
            'consentement_donnees': 'on',
        })
        self.assertContains(response, 'matricule est obligatoire')

    def test_numero_adherent_deja_utilise_est_refuse_sans_creer_de_compte(self):
        Utilisateur.objects.create_user(
            email='fm6-existant@example.com',
            password='mot-de-passe-solide',
            nom='Existant',
            prenom='FM6',
            role=Utilisateur.CLIENT_FM6,
            matricule='FM6-UNIQUE-1',
        )

        response = self.client.post(reverse('accounts:inscription'), {
            'role': Utilisateur.CLIENT_FM6,
            'email': 'fm6-duplicata@example.com',
            'nom': 'Duplicata',
            'prenom': 'FM6',
            'matricule': ' FM6-UNIQUE-1 ',
            'password1': 'Mot-de-passe-tres-solide-2027',
            'password2': 'Mot-de-passe-tres-solide-2027',
            'consentement_donnees': 'on',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ce numéro d&#x27;adhérent est déjà utilisé.")
        self.assertFalse(Utilisateur.objects.filter(email='fm6-duplicata@example.com').exists())

    def test_numero_adherent_inexistant_est_accepte_et_normalise(self):
        response = self.client.post(reverse('accounts:inscription'), {
            'role': Utilisateur.CLIENT_FM6,
            'email': 'fm6-nouveau@example.com',
            'nom': 'Nouveau',
            'prenom': 'FM6',
            'matricule': ' FM6-NOUVEAU-1 ',
            'password1': 'Mot-de-passe-tres-solide-2027',
            'password2': 'Mot-de-passe-tres-solide-2027',
            'consentement_donnees': 'on',
        })

        self.assertRedirects(response, reverse('core:accueil'))
        self.assertEqual(
            Utilisateur.objects.get(email='fm6-nouveau@example.com').matricule,
            'FM6-NOUVEAU-1',
        )

    def test_base_de_donnees_impose_l_unicite_du_numero_adherent(self):
        Utilisateur.objects.create_user(
            email='premier@example.com', password='mot-de-passe', nom='Premier', prenom='FM6',
            role=Utilisateur.CLIENT_FM6, matricule='FM6-DB-1',
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Utilisateur.objects.create_user(
                email='second@example.com', password='mot-de-passe', nom='Second', prenom='FM6',
                role=Utilisateur.CLIENT_FM6, matricule='FM6-DB-1',
            )
