from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.db import transaction
from io import StringIO
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Utilisateur
from apartments.models import Appartement
from reservations.models import Reservation
from services.reservation_services import creer_reservation, chercher_appartements_disponibles
from .models import Paiement, ConfirmationEmail
from services.confirmation_queue import traiter_confirmations


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class VirementTests(TestCase):
    def setUp(self):
        self.voyageur = Utilisateur.objects.create_user(email='virement@example.com', password='test', nom='Client', prenom='Test')
        self.admin = Utilisateur.objects.create_superuser(email='admin-virement@example.com', password='test', nom='Admin', prenom='Test')
        self.appartement = Appartement.objects.create(titre='Appartement test', description='Séjour', capacite=2)
        self.reservation = creer_reservation(self.voyageur, self.appartement, date(2027, 7, 10), date(2027, 7, 12), accepter_politiques=True)
        self.url = reverse('payments:admin_valider', args=(self.reservation.pk,))
        self.data = {'reference_virement': 'BANQUE-TEST-001', 'paiement_verifie': 'on', 'client_contacte': 'on'}

    def valider(self):
        paiement = self.reservation.generer_paiement(Paiement.VIREMENT)
        paiement.effectuer(self.admin, reference='VIREMENT-TEST')
        self.reservation.refresh_from_db()
        return paiement

    @override_settings(PAYMENT_BANK_NAME='Banque test', PAYMENT_ACCOUNT_HOLDER='Titulaire test', PAYMENT_RIB='RIB-DE-TEST', SUPPORT_WHATSAPP_NUMBER='+212 600 000 000')
    def test_instructions_et_whatsapp_sans_confirmation_client(self):
        self.client.force_login(self.voyageur)
        url = reverse('payments:payer', args=(self.reservation.pk,))
        response = self.client.get(url)
        self.assertContains(response, 'RIB-DE-TEST')
        self.assertContains(response, 'https://wa.me/212600000000?text=')
        self.assertContains(response, self.reservation.numero_reservation)
        self.assertContains(response, 'ajoutez vous-même le reçu')
        self.assertNotContains(response, 'numero_carte')
        self.assertEqual(self.client.post(url, {'numero_carte': '4242424242424242'}).status_code, 405)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
        self.assertFalse(Paiement.objects.exists())
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.EN_ATTENTE)

    def test_coordonnees_manquantes_pas_de_faux_compte(self):
        self.client.force_login(self.voyageur)
        with override_settings(PAYMENT_BANK_NAME='', PAYMENT_RIB='', SUPPORT_WHATSAPP_NUMBER=''):
            response = self.client.get(reverse('payments:payer', args=(self.reservation.pk,)))
        self.assertContains(response, 'Coordonnées bancaires en attente de publication')
        self.assertNotContains(response, 'https://wa.me/')

    def test_administrateur_verifie_puis_email_unique_et_pdf(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {'reference_virement': 'REFERENCE'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Paiement.objects.exists())
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse('reservations:admin_liste'))
        self.reservation.refresh_from_db()
        paiement = Paiement.objects.get()
        self.assertEqual(self.reservation.statut, Reservation.CONFIRMEE)
        self.assertEqual(paiement.statut, Paiement.PAYE)
        self.assertEqual(paiement.valide_par, self.admin)
        self.assertEqual(paiement.reference_virement, self.data['reference_virement'])
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(ConfirmationEmail.objects.count(), 1)
        call_command('envoyer_confirmations', stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('50 %', email.body)
        self.assertIn('72 heures', email.body)
        self.assertNotIn('NON ANNULABLE', email.body)
        self.assertEqual(len(email.attachments), 1)
        self.assertTrue(email.attachments[0].content.startswith(b'%PDF'))
        self.client.post(self.url, self.data)
        call_command('envoyer_confirmations', stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)

    def test_modele_refuse_validation_par_client(self):
        paiement = self.reservation.generer_paiement(Paiement.VIREMENT)
        with self.assertRaises(PermissionDenied):
            paiement.effectuer(self.voyageur, reference='TEST')
        paiement.refresh_from_db()
        self.assertEqual(paiement.statut, Paiement.EN_ATTENTE)

    def test_validation_refuse_montant_incorrect(self):
        paiement = self.reservation.generer_paiement(Paiement.VIREMENT)
        Paiement.objects.filter(pk=paiement.pk).update(montant=1)
        with self.assertRaisesMessage(ValidationError, 'montant'):
            paiement.effectuer(self.admin, reference='TEST')
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.EN_ATTENTE)

    def test_limite_24_heures_libere_dates_et_refuse_validation(self):
        instant = timezone.now()
        Reservation.objects.filter(pk=self.reservation.pk).update(date_reservation=instant - timedelta(hours=24))
        self.client.force_login(self.admin)
        with patch('django.utils.timezone.now', return_value=instant):
            self.assertTrue(self.appartement.is_disponible(self.reservation.date_debut, self.reservation.date_fin))
            self.assertIn(self.appartement, chercher_appartements_disponibles(self.reservation.date_debut, self.reservation.date_fin))
            self.client.post(self.url, self.data)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.EXPIREE)
        self.assertFalse(Paiement.objects.filter(statut=Paiement.PAYE).exists())

    def test_validation_ne_peut_pas_chevaucher_autre_sejour(self):
        paiement = self.reservation.generer_paiement(Paiement.VIREMENT)
        autre = Utilisateur.objects.create_user(email='autre@example.com', nom='Autre', prenom='Client')
        Reservation.objects.create(client=autre, appartement=self.appartement, date_debut=self.reservation.date_debut, date_fin=self.reservation.date_fin, montant_total=1400, statut=Reservation.CONFIRMEE)
        with self.assertRaisesMessage(ValidationError, 'dates ne sont plus disponibles'):
            paiement.effectuer(self.admin, reference='TEST')

    def test_double_validation_modele_idempotente(self):
        paiement = self.valider()
        date_validation = paiement.date_paiement
        paiement.effectuer(self.admin, reference='AUTRE')
        self.assertFalse(paiement.validation_nouvelle)
        self.assertEqual(paiement.reference_virement, 'VIREMENT-TEST')
        self.assertEqual(paiement.date_paiement, date_validation)

    def test_isolation_et_conditions_publiques(self):
        self.assertContains(self.client.get(reverse('reservations:politiques_generales')), '72 heures')
        autre = Utilisateur.objects.create_user(email='autre@example.com', nom='Autre', prenom='Client')
        self.client.force_login(autre)
        self.assertEqual(self.client.get(reverse('payments:payer', args=(self.reservation.pk,))).status_code, 404)

    def test_remboursement_50_plus_de_72h_meme_apres_48h(self):
        self.valider()
        instant = self.reservation.arrivee_prevue - timedelta(days=4)
        Reservation.objects.filter(pk=self.reservation.pk).update(date_reservation=instant - timedelta(days=3))
        with patch('django.utils.timezone.now', return_value=instant):
            self.reservation.annuler()
        self.assertEqual(self.reservation.montant_remboursement, Decimal('700.00'))
        self.assertEqual(self.reservation.statut, Reservation.ANNULEE)
        self.assertTrue(self.appartement.is_disponible(self.reservation.date_debut, self.reservation.date_fin))
        self.reservation.annuler()
        self.assertEqual(self.reservation.montant_remboursement, Decimal('700.00'))

    def test_remboursement_50_dans_48h_si_arrivee_plus_72h(self):
        self.valider()
        self.reservation.annuler()
        self.assertEqual(self.reservation.montant_remboursement, Decimal('700.00'))

    def test_limite_72h_non_remboursable(self):
        self.valider()
        with patch('django.utils.timezone.now', return_value=self.reservation.arrivee_prevue - timedelta(hours=72)):
            self.reservation.annuler()
        self.assertEqual(self.reservation.montant_remboursement, 0)

    def test_non_remboursable_moins_72h_meme_reservation_recente(self):
        self.valider()
        instant = self.reservation.arrivee_prevue - timedelta(hours=24)
        Reservation.objects.filter(pk=self.reservation.pk).update(date_reservation=instant - timedelta(hours=1))
        with patch('django.utils.timezone.now', return_value=instant):
            self.reservation.annuler()
        self.assertEqual(self.reservation.montant_remboursement, 0)

    def test_erreur_etablissement_100_meme_moins_72h(self):
        self.valider()
        with patch('django.utils.timezone.now', return_value=self.reservation.arrivee_prevue - timedelta(hours=1)):
            self.reservation.annuler('ERREUR_ETABLISSEMENT', administrateur=self.admin)
        self.assertEqual(self.reservation.montant_remboursement, Decimal('1400.00'))

    def test_client_ne_peut_pas_declarer_erreur_etablissement(self):
        self.valider()
        with self.assertRaises(ValidationError):
            self.reservation.annuler('ERREUR_ETABLISSEMENT', administrateur=self.voyageur)

    def test_no_show_zero_et_interdit_avant_arrivee(self):
        self.valider()
        with self.assertRaises(ValidationError):
            self.reservation.annuler('NO_SHOW', administrateur=self.admin)
        with patch('django.utils.timezone.now', return_value=self.reservation.arrivee_prevue + timedelta(days=1)):
            self.reservation.annuler('NO_SHOW', administrateur=self.admin)
        self.assertEqual(self.reservation.montant_remboursement, 0)


    def test_rollback_paiement_annule_la_tache(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.valider()
                raise RuntimeError('rollback')
        self.assertFalse(ConfirmationEmail.objects.exists())
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.EN_ATTENTE)

    @patch('services.confirmation_queue.envoyer_email_confirmation')
    def test_echec_repris_plus_tard_et_sans_doublon(self, envoyer):
        self.valider()
        envoyer.side_effect = OSError('SMTP indisponible')
        with self.assertLogs('services.confirmation_queue', level='ERROR'):
            self.assertEqual(traiter_confirmations(), (0, 1))
        tache = ConfirmationEmail.objects.get()
        self.assertIsNone(tache.envoye_le)
        self.assertEqual(tache.tentatives, 1)
        self.assertEqual(traiter_confirmations(), (0, 0))
        envoyer.side_effect = None
        envoyer.return_value = 1
        with patch('services.confirmation_queue.timezone.now', return_value=tache.disponible_le):
            self.assertEqual(traiter_confirmations(), (1, 0))
            self.assertEqual(traiter_confirmations(), (0, 0))
        self.assertEqual(envoyer.call_count, 2)

    @patch('services.confirmation_queue.envoyer_email_confirmation', return_value=1)
    def test_reprise_apres_interruption_worker(self, envoyer):
        from uuid import uuid4
        self.valider()
        maintenant = timezone.now()
        ConfirmationEmail.objects.update(verrou=uuid4(), disponible_le=maintenant + timedelta(minutes=15))
        self.assertEqual(traiter_confirmations(), (0, 0))
        with patch('services.confirmation_queue.timezone.now', return_value=maintenant + timedelta(minutes=16)):
            self.assertEqual(traiter_confirmations(), (1, 0))
        envoyer.assert_called_once()

    def test_pages_ne_declenchent_pas_expiration_globale(self):
        Reservation.objects.filter(pk=self.reservation.pk).update(date_reservation=timezone.now() - timedelta(hours=25))
        with patch.object(Reservation, 'expirer_en_attente', side_effect=AssertionError('Expiration globale HTTP')):
            self.client.force_login(self.voyageur)
            self.assertEqual(self.client.get(reverse('reservations:mes_reservations')).status_code, 200)
            self.client.force_login(self.admin)
            for url in ('reservations:admin_liste', 'dashboard:index', 'dashboard:export_excel'):
                self.assertEqual(self.client.get(reverse(url)).status_code, 200)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.EN_ATTENTE)
        call_command('expirer_reservations', stdout=StringIO())
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, Reservation.EXPIREE)
