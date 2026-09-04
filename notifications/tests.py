from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import Utilisateur
from apartments.models import Appartement
from payments.models import Paiement
from reservations.models import Reservation
from services.reservation_services import creer_reservation

from .models import Notification


class NotificationExpirationReservationTests(TestCase):
    def setUp(self):
        self.client = Utilisateur.objects.create_user(
            email='expiration@example.com',
            password='mot-de-passe',
            nom='Expire',
            prenom='Client',
        )
        self.appartement = Appartement.objects.create(
            titre='Studio notification',
            description='Appartement de test',
            prix_par_nuit=Decimal('700.00'),
            capacite=2,
        )
        self.reservation = creer_reservation(
            self.client,
            self.appartement,
            date(2027, 6, 10),
            date(2027, 6, 12),
        )

    def rendre_reservation_ancienne(self):
        Reservation.objects.filter(pk=self.reservation.pk).update(
            date_reservation=timezone.now() - timedelta(hours=25)
        )
        self.reservation.refresh_from_db()

    def test_expiration_cree_et_envoie_une_notification_au_client(self):
        self.rendre_reservation_ancienne()

        self.assertEqual(Reservation.expirer_en_attente(), 1)

        self.reservation.refresh_from_db()
        notification = Notification.objects.get(
            reservation=self.reservation,
            categorie=Notification.EXPIRATION_RESERVATION,
        )
        self.assertEqual(self.reservation.statut, Reservation.EXPIREE)
        self.assertEqual(notification.client, self.client)
        self.assertIsNotNone(notification.date_envoi)
        self.assertFalse(notification.lue)
        self.assertIn(self.reservation.numero_reservation, notification.message)
        self.assertIn("paiement n'a pas été effectué", notification.message)
        self.assertIn('24 heures', notification.message)

    def test_expiration_est_idempotente(self):
        self.rendre_reservation_ancienne()

        self.assertEqual(Reservation.expirer_en_attente(), 1)
        self.assertEqual(Reservation.expirer_en_attente(), 0)

        self.assertEqual(
            Notification.objects.filter(
                reservation=self.reservation,
                categorie=Notification.EXPIRATION_RESERVATION,
            ).count(),
            1,
        )

    def test_reservation_de_moins_de_24_heures_n_expire_pas(self):
        self.assertEqual(Reservation.expirer_en_attente(), 0)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.EN_ATTENTE)
        self.assertFalse(Notification.objects.exists())

    def test_reservation_payee_n_expire_pas(self):
        self.rendre_reservation_ancienne()
        Paiement.objects.create(
            reservation=self.reservation,
            montant=self.reservation.montant_total,
            methode=Paiement.CARTE,
            statut=Paiement.PAYE,
            date_paiement=timezone.now(),
        )

        self.assertEqual(Reservation.expirer_en_attente(), 0)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.EN_ATTENTE)
        self.assertFalse(Notification.objects.exists())

    def test_commande_expire_et_notifie_les_clients(self):
        self.rendre_reservation_ancienne()
        sortie = StringIO()

        call_command('expirer_reservations', stdout=sortie)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.EXPIREE)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertIn('1 réservation(s)', sortie.getvalue())
