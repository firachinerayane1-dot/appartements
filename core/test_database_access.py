from datetime import date
from unittest.mock import patch

from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import Utilisateur
from apartments.models import Appartement, PeriodeVacances, Photo
from core.db_monitoring import SlowQueryMiddleware
from notifications.models import Notification
from reservations.models import Reservation


class ListAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = Utilisateur.objects.create_user(email='list@example.com')
        cls.other = Utilisateur.objects.create_user(email='other@example.com')
        cls.admin = Utilisateur.objects.create_user(email='admin@example.com', role=Utilisateur.ADMINISTRATEUR)
        cls.apartments = Appartement.objects.bulk_create([
            Appartement(titre='Même titre', description='Test') for _ in range(25)
        ])
        Photo.objects.bulk_create([
            Photo(appartement=a, image=f'photo-{i}.jpg', principale=(i == 4))
            for a in cls.apartments for i in range(6)
        ])
        Reservation.objects.bulk_create([
            Reservation(client=cls.user, appartement=cls.apartments[i],
                        date_debut=date(2027, 1, 1), date_fin=date(2027, 1, 2),
                        statut=Reservation.ANNULEE if i else Reservation.CONFIRMEE,
                        montant_total=700) for i in range(25)
        ])
        Notification.objects.bulk_create([
            Notification(client=cls.user, message=f'Notification {i}') for i in range(25)
        ] + [Notification(client=cls.other, message='Privée')])
        PeriodeVacances.objects.bulk_create([
            PeriodeVacances(appartement=a, date_debut=date(2027, 1, 1),
                           date_fin=date(2027, 1, 2), libelle='Test') for a in cls.apartments
        ])

    def test_client_pages_and_global_counts(self):
        self.client.force_login(self.user)
        url = reverse('reservations:mes_reservations')
        with CaptureQueriesContext(connection) as queries:
            first = self.client.get(url)
            captured = list(queries)
        second = self.client.get(url, {'page': 2})
        self.assertEqual(len(first.context['reservations']), 12)
        self.assertEqual(second.context['reservations_total'], 25)
        self.assertEqual(second.context['reservations_confirmees'], 1)
        self.assertFalse({r.pk for r in first.context['reservations']} & {r.pk for r in second.context['reservations']})
        for r in first.context['reservations']:
            self.assertEqual(len(r.appartement.photos_reservation), 1)
            self.assertTrue(r.appartement.photos_reservation[0].principale)
        photo_queries = [q['sql'] for q in captured if 'apartments_photo' in q['sql'] and 'ROW_NUMBER()' in q['sql']]
        self.assertEqual(len(photo_queries), 1, [q['sql'] for q in captured])
        self.assertIn('ROW_NUMBER()', photo_queries[0])
        self.assertEqual(len(self.client.get(url, {'page': 999}).context['reservations']), 1)
        self.assertEqual(self.client.get(url, {'page': 'invalid'}).context['page_obj'].number, 1)

    def test_notifications_are_paginated_and_private(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('notifications:liste'), {'page': 2})
        self.assertEqual(len(response.context['notifications']), 5)
        self.assertEqual(response.context['page_obj'].paginator.count, 25)
        self.assertNotContains(response, 'Privée')

    def test_admin_lists(self):
        self.client.force_login(self.admin)
        for url, key in [('apartments:admin_liste', 'appartements'), ('apartments:vacances_liste', 'periodes'), ('reservations:admin_liste', 'reservations')]:
            with self.subTest(url=url):
                response = self.client.get(reverse(url), {'page': 2})
                self.assertEqual(len(response.context[key]), 5)
                self.assertContains(response, 'Précédent')
        response = self.client.get(reverse('apartments:admin_liste'))
        self.assertTrue(all(len(a.photos_admin) == 1 for a in response.context['appartements']))

    def test_search_fetches_only_three_photos_per_apartment(self):
        response = self.client.get(reverse('apartments:liste'), {'date_debut': '2027-02-01', 'date_fin': '2027-02-02'})
        apartments = response.context['page_obj'].object_list
        self.assertEqual(len(apartments), 12)
        for apartment in apartments:
            self.assertEqual(len(apartment.photos_carte), 3)
            self.assertTrue(apartment.photos_carte[0].principale)


class SlowQueryTests(TestCase):
    @override_settings(DB_SLOW_QUERY_MS=1, DEBUG=False)
    def test_logs_duration_without_parameters(self):
        def response(request):
            with connection.cursor() as cursor:
                cursor.execute('SELECT %s', ['private-value'])
            return 'ok'
        with patch('core.db_monitoring.perf_counter', side_effect=[0, .010]):
            with self.assertLogs('core.slow_queries', level='WARNING') as logs:
                self.assertEqual(SlowQueryMiddleware(response)(RequestFactory().get('/')), 'ok')
        self.assertIn('duration_ms=10.00', logs.output[0])
        self.assertNotIn('private-value', logs.output[0])
        self.assertNotIn('SELECT', logs.output[0])
        self.assertEqual(connection.execute_wrappers, [])

    @override_settings(DB_SLOW_QUERY_MS=0)
    def test_disabled(self):
        with patch('core.db_monitoring.perf_counter') as timer:
            SlowQueryMiddleware(lambda request: None)(RequestFactory().get('/'))
        timer.assert_not_called()
