from django.test import TestCase
from django.urls import reverse

from .models import Utilisateur


class InscriptionTests(TestCase):
    def test_pages_authentification_affichent_google(self):
        connexion = self.client.get(reverse('accounts:connexion'))
        inscription = self.client.get(reverse('accounts:inscription'))
        self.assertContains(connexion, 'Continuer avec Google')
        self.assertContains(inscription, 'S’inscrire avec Google')

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
