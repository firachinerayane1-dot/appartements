from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class PolitiqueConfidentialiteTests(TestCase):
    def test_page_est_publique_et_affiche_les_sections_principales(self):
        response = self.client.get(reverse('core:politique_confidentialite'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Politique de confidentialité')
        self.assertContains(response, 'FOSEH Safar')
        self.assertContains(response, 'Données collectées')
        self.assertContains(response, 'Durée de conservation')
        self.assertContains(response, 'Droits des utilisateurs')
        self.assertContains(response, 'service.client@fosehsafar.com')
from django.urls import reverse


class AccueilTests(TestCase):
    def test_accueil_est_public_et_dans_core(self):
        response = self.client.get(reverse('core:accueil'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/accueil.html')
        self.assertContains(response, 'Votre prochain séjour commence ici')
        self.assertNotContains(response, 'Notre sélection')
        self.assertNotContains(response, 'property-card')
        self.assertNotContains(response, 'map-label')
        self.assertNotContains(response, 'openstreetmap.org')
        self.assertContains(response, 'Ouvrir dans Google Maps')

    def test_feuille_de_style_est_trouvee(self):
        self.assertIsNotNone(finders.find('css/site.css'))
        self.assertIsNotNone(finders.find('accounts/auth.css'))
