from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


class AccueilTests(TestCase):
    def test_accueil_est_public_et_dans_core(self):
        response = self.client.get(reverse('core:accueil'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/accueil.html')
        self.assertContains(response, 'Votre prochain séjour commence ici')

    def test_feuille_de_style_est_trouvee(self):
        self.assertIsNotNone(finders.find('css/site.css'))
        self.assertIsNotNone(finders.find('accounts/auth.css'))
