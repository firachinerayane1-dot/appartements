from datetime import date, timedelta
from decimal import Decimal

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Utilisateur
from apartments.models import Appartement, PeriodeVacances
from payments.models import Paiement
from services.reservation_services import chercher_appartements_disponibles, creer_reservation
from .models import Reservation


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
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

    def test_numero_reservation_est_genere_automatiquement_et_unique(self):
        premiere = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12)
        )
        seconde = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 12), date(2027, 7, 14)
        )

        self.assertRegex(premiere.numero_reservation, r'^[a-z]{2}[A-Z]{2}\d{5}$')
        self.assertRegex(seconde.numero_reservation, r'^[a-z]{2}[A-Z]{2}\d{5}$')
        self.assertNotEqual(premiere.numero_reservation, seconde.numero_reservation)
        self.assertEqual(premiere.generer_recap()['numero'], premiere.numero_reservation)

    def test_chevauchement_avec_reservation_existante_est_bloque(self):
        creer_reservation(self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12))
        with self.assertRaisesMessage(ValidationError, "pas disponible"):
            creer_reservation(self.enseignant, self.appartement, date(2027, 7, 11), date(2027, 7, 13))

    def test_paiement_confirme_et_interdit_ensuite_annulation(self):
        reservation = creer_reservation(self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12))
        reservation.accepter_politiques()
        paiement = reservation.generer_paiement(Paiement.CARTE)
        paiement.effectuer()
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.CONFIRMEE)
        with self.assertRaisesMessage(ValidationError, "ne peut pas être annulée"):
            reservation.annuler()

    def test_creation_envoie_email_politiques_avant_paiement(self):
        self.client.force_login(self.enseignant)
        response = self.client.post(
            reverse('reservations:reserver', args=(self.appartement.pk,)),
            {'date_debut': '2027-07-10', 'date_fin': '2027-07-12'},
        )

        reservation = Reservation.objects.get()
        self.assertRedirects(response, reverse('reservations:detail', args=(reservation.pk,)))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(reservation.numero_reservation, mail.outbox[0].subject)
        self.assertIn(
            reverse('reservations:politiques', args=(reservation.pk,)),
            mail.outbox[0].body,
        )
        self.assertIn("non remboursable", mail.outbox[0].body)

    def test_politiques_sont_obligatoires_avant_paiement(self):
        reservation = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12)
        )
        with self.assertRaisesMessage(ValidationError, "accepter les politiques"):
            reservation.generer_paiement(Paiement.CARTE)
        self.client.force_login(self.enseignant)

        response = self.client.get(reverse('payments:payer', args=(reservation.pk,)))
        self.assertRedirects(response, reverse('reservations:politiques', args=(reservation.pk,)))

        page_politiques = self.client.get(reverse('reservations:politiques', args=(reservation.pk,)))
        self.assertContains(page_politiques, "J’ai lu et j’accepte")
        response = self.client.post(reverse('reservations:politiques', args=(reservation.pk,)))
        self.assertRedirects(response, reverse('payments:payer', args=(reservation.pk,)))

        reservation.refresh_from_db()
        self.assertIsNotNone(reservation.politiques_acceptees_le)
        with self.assertRaisesMessage(ValidationError, "uniquement par carte"):
            reservation.generer_paiement('VIREMENT')
        page_paiement = self.client.get(reverse('payments:payer', args=(reservation.pk,)))
        self.assertEqual(page_paiement.status_code, 200)
        self.assertContains(page_paiement, "Paiement sécurisé par carte")
        self.assertNotContains(page_paiement, 'name="methode"')
        response = self.client.post(
            reverse('payments:payer', args=(reservation.pk,)),
            {
                'numero_carte': '4242 4242 4242 4242',
                'expiration': '12/30',
                'cvv': '123',
            },
        )
        paiement = Paiement.objects.get(reservation=reservation)
        self.assertRedirects(response, reverse('payments:recu', args=(paiement.pk,)))
        self.assertEqual(paiement.methode, Paiement.CARTE)
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.CONFIRMEE)

    def test_reservation_impayee_expire_apres_24_heures(self):
        reservation = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12)
        )
        Reservation.objects.filter(pk=reservation.pk).update(
            date_reservation=timezone.now() - timedelta(hours=25)
        )
        reservation.refresh_from_db()

        self.assertTrue(self.appartement.is_disponible(date(2027, 7, 10), date(2027, 7, 12)))
        self.assertIn(
            self.appartement,
            chercher_appartements_disponibles(date(2027, 7, 10), date(2027, 7, 12)),
        )
        self.client.force_login(self.enseignant)
        response = self.client.get(reverse('payments:payer', args=(reservation.pk,)))
        self.assertRedirects(response, reverse('reservations:detail', args=(reservation.pk,)))
        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.EXPIREE)

    def test_pages_client_et_dashboard_se_rendent(self):
        reservation = creer_reservation(self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12))
        self.client.force_login(self.enseignant)
        for url in (
            reverse('apartments:liste'), reverse('apartments:detail', args=(self.appartement.pk,)),
            reverse('reservations:mes_reservations'), reverse('reservations:detail', args=(reservation.pk,)),
            reverse('notifications:liste'), reverse('reservations:politiques', args=(reservation.pk,)),
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
