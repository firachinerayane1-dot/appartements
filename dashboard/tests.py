from datetime import date
from django.test import TestCase
from django.urls import reverse
from accounts.models import Utilisateur
from apartments.models import Appartement
from payments.models import Paiement
from reservations.models import Reservation


class AdministrationInterfaceTests(TestCase):
    def setUp(self):
        self.admin = Utilisateur.objects.create_superuser(email='admin-ui@example.com', password='test', nom='Admin', prenom='Test')
        self.voyageur = Utilisateur.objects.create_user(email='client-ui@example.com', password='test', nom='Voyageur', prenom='Test')
        self.appartement = Appartement.objects.create(titre='Appartement de test', capacite=2)
        self.client.force_login(self.admin)

    def test_navigation_commune_et_formulaires(self):
        for name in ('dashboard:index', 'reservations:admin_liste', 'payments:admin_liste', 'apartments:admin_liste', 'apartments:creer', 'apartments:vacances_liste', 'apartments:vacances_creer'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'admin-workspace')
                self.assertContains(response, 'aria-label="Administration"')
                self.assertNotContains(response, 'class="site-footer"')

    def test_pagination_conserve_filtres_et_recherche(self):
        for index in range(21):
            Reservation.objects.create(client=self.voyageur, appartement=self.appartement, date_debut=date(2027, 7, 10), date_fin=date(2027, 7, 12), montant_total=1400, statut=Reservation.ANNULEE)
        response = self.client.get(reverse('reservations:admin_liste'), {'recherche': 'Voyageur', 'statut': 'ANNULEE'})
        self.assertEqual(len(response.context['reservations']), 20)
        self.assertEqual(response.context['page_obj'].paginator.count, 21)
        self.assertContains(response, 'recherche=Voyageur&amp;statut=ANNULEE&amp;page=2')
        response = self.client.get(reverse('reservations:admin_liste'), {'recherche': 'Voyageur', 'statut': 'ANNULEE', 'page': 2})
        self.assertEqual(len(response.context['reservations']), 1)
        response = self.client.get(reverse('reservations:admin_liste'), {'recherche': 'introuvable'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_filtre_paiement_invalide_affiche_erreur(self):
        response = self.client.get(reverse('payments:admin_liste'), {'date': 'pas-une-date'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertContains(response, 'errorlist')

    def test_filtres_paiements_restent_selectionnes(self):
        response = self.client.get(reverse('payments:admin_liste'), {'statut': Paiement.PAYE, 'methode': Paiement.VIREMENT, 'date': '2026-01-15'})
        self.assertContains(response, 'value="PAYE" selected')
        self.assertContains(response, 'value="VIREMENT" selected')
        self.assertContains(response, 'value="2026-01-15"')

    def test_periode_invalide_affiche_erreur(self):
        response = self.client.get(reverse('dashboard:index'), {'date_debut': '2026-02-01'})
        self.assertContains(response, 'Saisissez les deux bornes')

    def test_client_ne_peut_pas_acceder_aux_listes_admin(self):
        self.client.force_login(self.voyageur)
        for name in ('dashboard:index', 'reservations:admin_liste', 'payments:admin_liste', 'apartments:admin_liste'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
