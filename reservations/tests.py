from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Utilisateur
from apartments.models import Appartement, PeriodeVacances
from payments.models import Paiement
from services.reservation_services import creer_reservation
from .models import Reservation


class ReglesReservationTests(TestCase):
    def setUp(self):
        self.client_regulier = Utilisateur.objects.create_user(
            email='client@example.com', password='mot-de-passe', nom='Client', prenom='Claude'
        )
        self.enseignant = Utilisateur.objects.create_user(
            email='prof@example.com', password='mot-de-passe', nom='Prof', prenom='Emma',
            role=Utilisateur.ENSEIGNANT, matricule='ENS-1'
        )
        self.appartement = Appartement.objects.create(
            titre='Studio', description='Centre-ville', prix_par_nuit=Decimal('100.00'), capacite=2
        )
        PeriodeVacances.objects.create(
            appartement=self.appartement, libelle='Été', date_debut=date(2027, 7, 1), date_fin=date(2027, 9, 1)
        )

    def test_vacances_bloquent_client_regulier(self):
        with self.assertRaisesMessage(ValidationError, "qu'aux enseignants"):
            creer_reservation(self.client_regulier, self.appartement, date(2027, 7, 10), date(2027, 7, 12))

    def test_enseignant_peut_reserver_pendant_vacances(self):
        reservation = creer_reservation(self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12))
        self.assertEqual(reservation.statut, Reservation.EN_ATTENTE)
        self.assertEqual(reservation.montant_total, Decimal('170.00'))

    def test_chevauchement_avec_reservation_existante_est_bloque(self):
        creer_reservation(self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12))
        with self.assertRaisesMessage(ValidationError, "pas disponible"):
            creer_reservation(self.enseignant, self.appartement, date(2027, 7, 11), date(2027, 7, 13))

    def test_paiement_confirme_et_annulation_notifie(self):
        reservation = creer_reservation(self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12))
        paiement = reservation.generer_paiement(Paiement.VIREMENT)
        paiement.effectuer()
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.CONFIRMEE)
        reservation.annuler()
        self.assertEqual(self.enseignant.notifications.count(), 1)
        self.assertIsNotNone(self.enseignant.notifications.get().date_envoi)

    def test_pages_client_et_dashboard_se_rendent(self):
        reservation = creer_reservation(self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12))
        self.client.force_login(self.enseignant)
        for url in (
            reverse('apartments:liste'), reverse('apartments:detail', args=(self.appartement.pk,)),
            reverse('reservations:mes_reservations'), reverse('reservations:detail', args=(reservation.pk,)),
            reverse('notifications:liste'), reverse('payments:payer', args=(reservation.pk,)),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

        admin = Utilisateur.objects.create_superuser(
            email='admin@example.com', password='mot-de-passe', nom='Admin', prenom='Ada'
        )
        self.client.force_login(admin)
        for url in (
            reverse('dashboard:index'), reverse('apartments:admin_liste'),
            reverse('apartments:vacances_liste'), reverse('reservations:admin_liste'),
            reverse('payments:admin_liste'),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)
