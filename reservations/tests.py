from datetime import date, timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.core import mail
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from accounts.models import Utilisateur
from apartments.models import Appartement, PeriodeVacances
from payments.models import Paiement
from services.reservation_services import (
    MESSAGE_AOUT_RESERVE_FM6,
    chercher_appartements_disponibles,
    creer_reservation,
    modifier_reservation,
)
from .models import Reservation


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class ReglesReservationTests(TestCase):
    def setUp(self):
        self.client_regulier = Utilisateur.objects.create_user(
            email='client@example.com', password='mot-de-passe', nom='Client', prenom='Claude'
        )
        self.enseignant = Utilisateur.objects.create_user(
            email='prof@example.com', password='mot-de-passe', nom='Prof', prenom='Emma',
            role=Utilisateur.CLIENT_FM6, matricule='FM6-1'
        )
        self.appartement = Appartement.objects.create(
            titre='Studio',
            description='Centre-ville',
            prix_par_nuit=Decimal('700.00'),
            prix_fm6_par_nuit=Decimal('500.00'),
            capacite=2,
        )
        PeriodeVacances.objects.create(
            appartement=self.appartement, libelle='Été', date_debut=date(2027, 7, 1), date_fin=date(2027, 9, 1)
        )

    def test_client_regulier_peut_reserver_pendant_les_vacances(self):
        reservation = creer_reservation(
            self.client_regulier,
            self.appartement,
            date(2027, 7, 10),
            date(2027, 7, 12),
        )

        self.assertEqual(reservation.statut, Reservation.EN_ATTENTE)
        self.assertEqual(reservation.montant_total, Decimal('1400.00'))

    def test_client_fm6_paie_500_dh_la_nuit(self):
        reservation = creer_reservation(self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 12))
        self.assertEqual(reservation.statut, Reservation.EN_ATTENTE)
        self.assertEqual(reservation.montant_total, Decimal('1000.00'))

    def test_client_regulier_paie_700_dh_la_nuit(self):
        montant = self.appartement.calculer_prix(
            date(2027, 6, 10),
            date(2027, 6, 12),
            self.client_regulier,
        )

        self.assertEqual(montant, Decimal('1400.00'))

    def test_tarifs_sont_propres_a_l_appartement_et_au_type_de_client(self):
        appartement_premium = Appartement.objects.create(
            titre='Premium',
            description='Test des tarifs',
            prix_par_nuit=Decimal('1000.00'),
            prix_fm6_par_nuit=Decimal('700.00'),
            capacite=4,
        )

        self.assertEqual(
            appartement_premium.calculer_prix(
                date(2027, 6, 10), date(2027, 6, 12), self.client_regulier
            ),
            Decimal('2000.00'),
        )
        self.assertEqual(
            appartement_premium.calculer_prix(
                date(2027, 6, 10), date(2027, 6, 12), self.enseignant
            ),
            Decimal('1400.00'),
        )

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
        with self.assertRaisesMessage(ValidationError, Reservation.MESSAGE_CHEVAUCHEMENT_ADHERENT):
            creer_reservation(self.enseignant, self.appartement, date(2027, 7, 11), date(2027, 7, 13))

    def test_chevauchement_du_meme_adherent_sur_deux_appartements_est_bloque(self):
        autre_appartement = Appartement.objects.create(
            titre='Autre studio', description='Ailleurs', capacite=2
        )
        creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 15)
        )

        with self.assertRaisesMessage(
            ValidationError,
            Reservation.MESSAGE_CHEVAUCHEMENT_ADHERENT,
        ):
            creer_reservation(
                self.enseignant,
                autre_appartement,
                date(2027, 7, 12),
                date(2027, 7, 18),
            )

        self.assertEqual(Reservation.objects.count(), 1)

    def test_client_regulier_ne_peut_pas_reserver_deux_logements_sur_la_meme_periode(self):
        autre_appartement = Appartement.objects.create(
            titre='Appartement régulier', description='Ailleurs', capacite=2
        )

        creer_reservation(
            self.client_regulier,
            self.appartement,
            date(2027, 7, 10),
            date(2027, 7, 15),
        )
        with self.assertRaisesMessage(
            ValidationError,
            Reservation.MESSAGE_CHEVAUCHEMENT_ADHERENT,
        ):
            creer_reservation(
                self.client_regulier,
                autre_appartement,
                date(2027, 7, 12),
                date(2027, 7, 17),
            )

        self.assertEqual(Reservation.objects.count(), 1)

    def test_client_regulier_ne_voit_aucun_appartement_pour_aout(self):
        self.assertFalse(
            chercher_appartements_disponibles(
                date(2027, 8, 10),
                date(2027, 8, 12),
                self.client_regulier,
            ).exists()
        )

    def test_creation_directe_en_aout_est_refusee_au_client_regulier(self):
        with self.assertRaisesMessage(ValidationError, MESSAGE_AOUT_RESERVE_FM6):
            creer_reservation(
                self.client_regulier,
                self.appartement,
                date(2027, 8, 10),
                date(2027, 8, 12),
            )

        self.assertFalse(Reservation.objects.exists())

    def test_client_fm6_peut_reserver_en_aout(self):
        reservation = creer_reservation(
            self.enseignant,
            self.appartement,
            date(2027, 8, 10),
            date(2027, 8, 12),
        )

        self.assertEqual(reservation.get_duree(), 2)

    def test_bornes_du_mois_aout_respectent_le_depart_exclu(self):
        juillet = creer_reservation(
            self.client_regulier,
            self.appartement,
            date(2027, 7, 31),
            date(2027, 8, 1),
        )
        septembre = creer_reservation(
            self.client_regulier,
            self.appartement,
            date(2027, 9, 1),
            date(2027, 9, 2),
        )

        self.assertEqual(juillet.get_duree(), 1)
        self.assertEqual(septembre.get_duree(), 1)

    def test_modification_vers_aout_est_refusee_au_client_regulier(self):
        reservation = creer_reservation(
            self.client_regulier,
            self.appartement,
            date(2027, 7, 10),
            date(2027, 7, 12),
        )

        with self.assertRaisesMessage(ValidationError, MESSAGE_AOUT_RESERVE_FM6):
            modifier_reservation(
                reservation,
                date_debut=date(2027, 8, 10),
                date_fin=date(2027, 8, 12),
            )

        reservation.refresh_from_db()
        self.assertEqual(reservation.date_debut, date(2027, 7, 10))

    def test_reservation_fm6_est_limitee_a_cinq_nuits(self):
        with self.assertRaisesMessage(ValidationError, Reservation.MESSAGE_DUREE_FM6):
            creer_reservation(
                self.enseignant,
                self.appartement,
                date(2027, 1, 1),
                date(2027, 1, 7),
            )

        self.assertFalse(Reservation.objects.exists())

    def test_client_regulier_n_est_pas_soumis_aux_limites_fm6(self):
        premiere = creer_reservation(
            self.client_regulier,
            self.appartement,
            date(2027, 1, 1),
            date(2027, 1, 7),
        )
        seconde = creer_reservation(
            self.client_regulier,
            self.appartement,
            date(2027, 1, 7),
            date(2027, 1, 13),
        )

        self.assertEqual(premiere.get_duree() + seconde.get_duree(), 12)

    def test_fm6_peut_faire_dix_reservations_d_une_nuit_dans_l_annee(self):
        for jour in range(1, 11):
            creer_reservation(
                self.enseignant,
                self.appartement,
                date(2027, 1, jour),
                date(2027, 1, jour + 1),
            )

        self.assertEqual(Reservation.objects.count(), 10)
        self.assertEqual(
            sum(reservation.get_duree() for reservation in Reservation.objects.all()),
            10,
        )

    def test_onzieme_nuit_fm6_de_l_annee_est_refusee(self):
        creer_reservation(
            self.enseignant, self.appartement, date(2027, 1, 1), date(2027, 1, 6)
        )
        creer_reservation(
            self.enseignant, self.appartement, date(2027, 1, 6), date(2027, 1, 11)
        )

        message = Reservation.MESSAGE_QUOTA_ANNUEL_FM6.format(annee=2027)
        with self.assertRaisesMessage(ValidationError, message):
            creer_reservation(
                self.enseignant,
                self.appartement,
                date(2027, 1, 11),
                date(2027, 1, 12),
            )

        self.assertEqual(Reservation.objects.count(), 2)

    def test_reservation_annulee_ne_consomme_pas_le_quota_annuel_fm6(self):
        a_annuler = creer_reservation(
            self.enseignant, self.appartement, date(2027, 1, 1), date(2027, 1, 6)
        )
        creer_reservation(
            self.enseignant, self.appartement, date(2027, 1, 6), date(2027, 1, 11)
        )
        a_annuler.annuler()

        remplacement = creer_reservation(
            self.enseignant, self.appartement, date(2027, 2, 1), date(2027, 2, 6)
        )

        self.assertEqual(remplacement.get_duree(), 5)

    def test_nuits_fm6_sont_imputees_a_leur_annee_civile(self):
        reservation = creer_reservation(
            self.enseignant,
            self.appartement,
            date(2027, 12, 29),
            date(2028, 1, 3),
        )

        self.assertEqual(reservation.get_duree(), 5)
        seconde = creer_reservation(
            self.enseignant,
            self.appartement,
            date(2028, 1, 3),
            date(2028, 1, 8),
        )
        self.assertEqual(seconde.get_duree(), 5)

    def test_modification_ne_peut_pas_depasser_le_quota_annuel_fm6(self):
        creer_reservation(
            self.enseignant, self.appartement, date(2027, 1, 1), date(2027, 1, 4)
        )
        creer_reservation(
            self.enseignant, self.appartement, date(2027, 1, 4), date(2027, 1, 7)
        )
        a_modifier = creer_reservation(
            self.enseignant, self.appartement, date(2027, 1, 7), date(2027, 1, 11)
        )

        message = Reservation.MESSAGE_QUOTA_ANNUEL_FM6.format(annee=2027)
        with self.assertRaisesMessage(ValidationError, message):
            modifier_reservation(
                a_modifier,
                date_debut=date(2027, 1, 7),
                date_fin=date(2027, 1, 12),
            )

        a_modifier.refresh_from_db()
        self.assertEqual(a_modifier.date_fin, date(2027, 1, 11))

    def test_vue_affiche_le_conflit_adherent_sans_creation_partielle(self):
        autre_appartement = Appartement.objects.create(
            titre='Studio disponible', description='Ailleurs', capacite=2
        )
        creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 15)
        )
        self.client.force_login(self.enseignant)

        response = self.client.post(
            reverse('reservations:reserver', args=(autre_appartement.pk,)),
            {'date_debut': '2027-07-12', 'date_fin': '2027-07-18'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, Reservation.MESSAGE_CHEVAUCHEMENT_ADHERENT)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_periodes_non_chevauchantes_du_meme_adherent_sont_acceptees(self):
        premiere = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 15)
        )
        seconde = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 15), date(2027, 7, 20)
        )

        self.assertEqual({premiere.pk, seconde.pk}, set(Reservation.objects.values_list('pk', flat=True)))

    def test_reservation_annulee_ne_bloque_pas_la_meme_periode(self):
        annulee = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 15)
        )
        annulee.annuler()

        nouvelle = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 15)
        )

        self.assertEqual(nouvelle.statut, Reservation.EN_ATTENTE)

    def test_modification_sans_conflit_est_acceptee(self):
        reservation = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 15)
        )

        modifiee = modifier_reservation(
            reservation,
            date_debut=date(2027, 7, 16),
            date_fin=date(2027, 7, 20),
        )

        self.assertEqual(modifiee.date_debut, date(2027, 7, 16))
        self.assertEqual(modifiee.date_fin, date(2027, 7, 20))

    def test_modification_avec_conflit_est_refusee(self):
        premiere = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 15)
        )
        seconde = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 16), date(2027, 7, 20)
        )

        with self.assertRaisesMessage(
            ValidationError,
            Reservation.MESSAGE_CHEVAUCHEMENT_ADHERENT,
        ):
            modifier_reservation(
                seconde,
                date_debut=date(2027, 7, 14),
                date_fin=date(2027, 7, 18),
            )

        seconde.refresh_from_db()
        self.assertEqual(seconde.date_debut, date(2027, 7, 16))
        self.assertEqual(premiere.date_fin, date(2027, 7, 15))

    def test_reservation_ne_se_considere_pas_comme_son_propre_conflit(self):
        reservation = creer_reservation(
            self.enseignant, self.appartement, date(2027, 7, 10), date(2027, 7, 15)
        )

        reservation.full_clean()

        self.assertFalse(reservation.reservations_adherent_en_conflit().exists())

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
        self.assertIn("Garantie", mail.outbox[0].body)
        self.assertIn("Départ tardif", mail.outbox[0].body)
        self.assertIn("Non-présentation", mail.outbox[0].body)
        self.assertIn("Check-in", mail.outbox[0].body)

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
        self.assertContains(page_politiques, "Garantie")
        self.assertContains(page_politiques, "Attribution du logement")
        self.assertContains(page_politiques, "Départ tardif")
        self.assertContains(page_politiques, "Non-présentation")
        self.assertContains(page_politiques, "1 000,00 MAD")
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
        self.assertEqual(len(mail.outbox), 1)
        confirmation = mail.outbox[0]
        self.assertEqual(
            confirmation.subject,
            f'Booking Reference Number {reservation.numero_reservation} - CONFIRMED, FOSE SAFAR',
        )
        self.assertTrue(confirmation.from_email.startswith('FOSE Safar <'))
        self.assertIn('NON ANNULABLE - NON REMBOURSABLE', confirmation.body)
        self.assertIn(reservation.appartement.titre, confirmation.body)
        self.assertEqual(len(confirmation.alternatives), 1)
        self.assertIn('Votre séjour est confirmé', confirmation.alternatives[0].content)
        self.assertEqual(len(confirmation.attachments), 1)
        piece_jointe = confirmation.attachments[0]
        self.assertEqual(
            piece_jointe.filename,
            f'confirmation-reservation-{reservation.numero_reservation}.pdf',
        )
        self.assertEqual(piece_jointe.mimetype, 'application/pdf')
        self.assertTrue(piece_jointe.content.startswith(b'%PDF'))
        self.assertGreater(len(piece_jointe.content), 20_000)

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
            reverse('apartments:liste'),
            f"{reverse('apartments:detail', args=(self.appartement.pk,))}"
            '?date_debut=2027-06-10&date_fin=2027-06-12',
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


@skipUnlessDBFeature('has_select_for_update')
class ConcurrenceReservationTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.adherent = Utilisateur.objects.create_user(
            email='concurrent@example.com',
            password='mot-de-passe',
            nom='Concurrent',
            prenom='Client',
            role=Utilisateur.CLIENT_FM6,
            matricule='FM6-CONCURRENT',
        )
        self.appartements = [
            Appartement.objects.create(titre=f'Studio {numero}', description='Test', capacite=2)
            for numero in (1, 2)
        ]

    def test_deux_requetes_concurrentes_ne_creent_pas_de_chevauchement(self):
        barriere = Barrier(2)

        def reserver(appartement_id):
            close_old_connections()
            try:
                adherent = Utilisateur.objects.get(pk=self.adherent.pk)
                appartement = Appartement.objects.get(pk=appartement_id)
                barriere.wait(timeout=5)
                reservation = creer_reservation(
                    adherent,
                    appartement,
                    date(2027, 10, 10),
                    date(2027, 10, 15),
                )
                return ('cree', reservation.pk)
            except ValidationError as exc:
                return ('refuse', exc.messages[0])
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(
                reserver,
                [appartement.pk for appartement in self.appartements],
            ))

        self.assertEqual(sorted(resultat[0] for resultat in resultats), ['cree', 'refuse'])
        self.assertEqual(Reservation.objects.count(), 1)
        self.assertIn(
            Reservation.MESSAGE_CHEVAUCHEMENT_ADHERENT,
            [resultat[1] for resultat in resultats if resultat[0] == 'refuse'],
        )

    def test_deux_requetes_concurrentes_ne_depassent_pas_le_quota_annuel(self):
        creer_reservation(
            self.adherent,
            self.appartements[0],
            date(2027, 1, 1),
            date(2027, 1, 6),
        )
        creer_reservation(
            self.adherent,
            self.appartements[0],
            date(2027, 1, 6),
            date(2027, 1, 10),
        )
        barriere = Barrier(2)

        def reserver(appartement_id, debut, fin):
            close_old_connections()
            try:
                adherent = Utilisateur.objects.get(pk=self.adherent.pk)
                appartement = Appartement.objects.get(pk=appartement_id)
                barriere.wait(timeout=5)
                reservation = creer_reservation(adherent, appartement, debut, fin)
                return ('cree', reservation.pk)
            except ValidationError as exc:
                return ('refuse', exc.messages[0])
            finally:
                close_old_connections()

        demandes = (
            (self.appartements[0].pk, date(2027, 1, 10), date(2027, 1, 11)),
            (self.appartements[1].pk, date(2027, 1, 11), date(2027, 1, 12)),
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(reserver, *demande) for demande in demandes]
            resultats = [future.result() for future in futures]

        self.assertEqual(sorted(resultat[0] for resultat in resultats), ['cree', 'refuse'])
        self.assertEqual(Reservation.objects.count(), 3)
        self.assertIn(
            Reservation.MESSAGE_QUOTA_ANNUEL_FM6.format(annee=2027),
            [resultat[1] for resultat in resultats if resultat[0] == 'refuse'],
        )
