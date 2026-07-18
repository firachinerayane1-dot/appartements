from datetime import date
from decimal import Decimal

from django.db.models import Prefetch
from django.test import TestCase
from django.urls import reverse

from accounts.models import Utilisateur
from reservations.models import Reservation
from services.reservation_services import chercher_appartements_disponibles

from .models import Appartement, Photo


class RechercheDisponibiliteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client_reservation = Utilisateur.objects.create_user(
            email='client-recherche@example.com',
            password='mot-de-passe',
            nom='Client',
            prenom='Recherche',
        )
        cls.libre = cls.creer_appartement('Appartement libre')
        cls.occupe = cls.creer_appartement('Appartement occupé')
        cls.relais = cls.creer_appartement('Appartement avec départ le jour même')
        cls.annule = cls.creer_appartement('Appartement avec réservation annulée')

        cls.creer_reservation(cls.occupe, date(2027, 8, 12), date(2027, 8, 18))
        cls.creer_reservation(cls.relais, date(2027, 8, 5), date(2027, 8, 10))
        cls.creer_reservation(
            cls.annule,
            date(2027, 8, 12),
            date(2027, 8, 18),
            statut=Reservation.ANNULEE,
        )

    @classmethod
    def creer_appartement(cls, titre):
        return Appartement.objects.create(
            titre=titre,
            description='Appartement de test',
            prix_par_nuit=Decimal('500.00'),
            capacite=2,
        )

    @classmethod
    def creer_reservation(cls, appartement, date_debut, date_fin, statut=Reservation.CONFIRMEE):
        return Reservation.objects.create(
            client=cls.client_reservation,
            appartement=appartement,
            date_debut=date_debut,
            date_fin=date_fin,
            statut=statut,
            montant_total=Decimal('1000.00'),
        )

    def test_recherche_exclut_uniquement_les_chevauchements_bloquants(self):
        response = self.client.get(
            reverse('apartments:liste'),
            {'date_debut': '2027-08-10', 'date_fin': '2027-08-15'},
        )

        appartements = list(response.context['page_obj'].object_list)
        self.assertIn(self.libre, appartements)
        self.assertIn(self.relais, appartements)
        self.assertIn(self.annule, appartements)
        self.assertNotIn(self.occupe, appartements)

    def test_bouton_reserver_transmet_les_dates(self):
        response = self.client.get(
            reverse('apartments:liste'),
            {'date_debut': '2027-08-10', 'date_fin': '2027-08-15'},
        )

        url = reverse('reservations:reserver', args=(self.libre.pk,))
        self.assertContains(
            response,
            f'{url}?date_debut=2027-08-10&amp;date_fin=2027-08-15',
        )

    def test_formulaire_de_reservation_est_pre_rempli(self):
        self.client.force_login(self.client_reservation)

        response = self.client.get(
            reverse('reservations:reserver', args=(self.libre.pk,)),
            {'date_debut': '2027-08-10', 'date_fin': '2027-08-15'},
        )

        self.assertEqual(response.context['form'].initial['date_debut'], '2027-08-10')
        self.assertEqual(response.context['form'].initial['date_fin'], '2027-08-15')

    def test_liste_et_photos_sont_chargees_en_deux_requetes(self):
        appartements = chercher_appartements_disponibles(
            date(2027, 8, 10),
            date(2027, 8, 15),
        ).prefetch_related(
            Prefetch(
                'photos',
                queryset=Photo.objects.order_by('-principale', 'pk'),
                to_attr='photos_carte',
            )
        )

        with self.assertNumQueries(2):
            resultat = list(appartements)
            for appartement in resultat:
                list(appartement.photos_carte)
