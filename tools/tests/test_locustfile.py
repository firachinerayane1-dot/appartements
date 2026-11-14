"""Tests sans serveur ni accès à la base applicative."""
import tempfile
import unittest
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, patch

from locust.env import Environment
from locust.exception import StopUser

from locustfile import BookingUser, BrowsingUser, Page, ProjectUser, read_accounts


class LoadScenarioTests(unittest.TestCase):
    def setUp(self):
        self.host_patch = patch.object(ProjectUser, 'host', 'https://example.test')
        self.host_patch.start()
        self.addCleanup(self.host_patch.stop)
        self.user = ProjectUser(Environment())
        self.user.client = MagicMock()
        self.user.wait = MagicMock()

    def response(self, method, status=200, text='', location=''):
        response = MagicMock(status_code=status, text=text, headers={'Location': location})
        getattr(self.user.client, method).return_value.__enter__.return_value = response
        return response

    def test_html_extracts_csrf_and_only_local_apartments(self):
        page = Page('''<input value="token" name="csrfmiddlewaretoken">
            <a href="/appartements/12/?date_debut=2027-01-01&amp;x=y">a</a>
            <a href="https://other.test/appartements/99/">b</a>
            <a href="/appartements/gestion/">c</a>''')
        self.assertEqual(page.csrf, 'token')
        self.assertEqual(page.apartments, {12})

    def test_http_200_failed_booking_is_reported(self):
        response = self.response('post', text='Dates indisponibles')
        result = self.user.post_form('/reserver/', 'booking', Page(''), {}, r'/paiements/\d+/')
        self.assertIsNone(result)
        response.failure.assert_called_once()

    def test_post_sends_csrf_and_validates_destination(self):
        response = self.response('post', 302, location='/paiements/reservation/73/')
        result = self.user.post_form('/reserver/', 'booking',
            Page('<input name="csrfmiddlewaretoken" value="rotated">'),
            {'accepter_politiques': 'on'}, r'/paiements/reservation/\d+/')
        self.assertEqual(result, '/paiements/reservation/73/')
        response.failure.assert_not_called()
        kwargs = self.user.client.post.call_args.kwargs
        self.assertEqual(kwargs['data']['csrfmiddlewaretoken'], 'rotated')
        self.assertEqual(kwargs['headers']['Referer'], 'https://example.test/reserver/')
        self.assertFalse(kwargs['allow_redirects'])

    def test_login_redirect_and_external_redirect_are_failures(self):
        for location in ['/accounts/connexion/', 'https://evil.test/paiements/reservation/73/']:
            with self.subTest(location=location):
                response = self.response('post', 302, location=location)
                self.assertIsNone(self.user.post_form('/reserver/', 'booking', Page(''), {},
                                                     r'/paiements/reservation/\d+/'))
                response.failure.assert_called_once()

    def test_missing_csrf_and_protected_redirect_are_failures(self):
        for status in [200, 302, 500]:
            response = self.response('get', status)
            self.assertIsNone(self.user.get_page('/accounts/profil/', 'profile', csrf=True))
            response.failure.assert_called_once()

    def test_csv_rejects_duplicate_accounts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'users.csv'
            path.write_text('email,password\na@example.test,p\na@example.test,q\n')
            with self.assertRaises(ValueError):
                read_accounts(path)

    def prepare_account(self):
        self.account = {'email': 'load@example.test', 'password': 'test-password'}
        self.user.environment.loadtest_accounts = Queue()
        self.user.environment.loadtest_accounts.put(self.account)

    def test_login_once_and_keep_session_across_journeys(self):
        self.prepare_account()
        form = Page('<input name="csrfmiddlewaretoken" value="token">')
        self.user.get_page = MagicMock(return_value=form)
        self.user.post_form = MagicMock(return_value='/accounts/profil/')
        self.user.search_and_book = MagicMock()

        self.user.on_start()
        self.assertTrue(self.user.environment.loadtest_accounts.empty())
        for book in (False, True, False, True):
            self.user.visit(book=book)
        self.user.post_form.assert_called_once()
        self.assertEqual(self.user.post_form.call_args.args[0], '/accounts/connexion/')
        self.assertEqual(self.user.search_and_book.call_count, 4)
        self.user.client.cookies.clear.assert_not_called()
        self.user.on_stop()
        self.user.on_stop()  # Repeated teardown must not duplicate the account.
        self.assertEqual(self.user.environment.loadtest_accounts.qsize(), 1)
        self.assertEqual(self.user.environment.loadtest_accounts.get_nowait(), self.account)

    def test_failed_login_stops_user_without_booking(self):
        self.prepare_account()
        self.user.get_page = MagicMock(return_value=Page('<input name="csrfmiddlewaretoken" value="t">'))
        self.user.post_form = MagicMock(return_value=None)
        self.user.search_and_book = MagicMock()
        with self.assertRaises(StopUser):
            self.user.on_start()
        self.user.search_and_book.assert_not_called()
        self.user.post_form.assert_called_once()
        self.user.on_stop()  # Locust calls on_stop when on_start raises StopUser.
        self.assertEqual(self.user.environment.loadtest_accounts.qsize(), 1)

    def test_missing_account_stops_user_before_http(self):
        self.user.environment.loadtest_accounts = Queue()
        self.user.login = MagicMock()
        with self.assertRaises(StopUser):
            self.user.on_start()
        self.user.login.assert_not_called()
        self.user.on_stop()
        self.assertTrue(self.user.environment.loadtest_accounts.empty())

    def test_browsing_user_never_opens_booking_form_or_posts(self):
        user = BrowsingUser(self.user.environment)
        user.wait = MagicMock()
        user.get_page = MagicMock(return_value=Page('<a href="/appartements/42/">A</a>'))
        user.post_form = MagicMock()
        user.browse()
        self.assertEqual([call.args[0] for call in user.get_page.call_args_list],
                         ['/', '/appartements/', '/appartements/42/'])
        user.post_form.assert_not_called()

    def test_booking_user_completes_journey_without_reauthenticating(self):
        user = BookingUser(self.user.environment)
        user.cleanup = False
        user.wait = MagicMock()
        user.get_page = MagicMock(return_value=Page(
            '<a href="/appartements/42/">A</a><input name="csrfmiddlewaretoken" value="t">'))
        user.post_form = MagicMock(return_value='/paiements/reservation/73/')
        user.reserve()
        user.post_form.assert_called_once()
        self.assertEqual(user.post_form.call_args.args[0], '/reservations/appartement/42/reserver/')
        self.assertEqual(user.get_page.call_args.args[0], '/reservations/73/')

    def test_locust_dispatches_seventy_thirty_user_mix(self):
        from locust.dispatch import UsersDispatcher
        from locust.runners import WorkerNode

        self.assertTrue(ProjectUser.abstract)
        self.assertFalse(BrowsingUser.abstract)
        self.assertFalse(BookingUser.abstract)
        for total, browsers, bookers in [(50, 35, 15), (75, 52, 23), (100, 70, 30), (500, 350, 150)]:
            with self.subTest(users=total):
                dispatcher = UsersDispatcher([WorkerNode('local')], [BrowsingUser, BookingUser])
                dispatcher.new_dispatch(target_user_count=total, spawn_rate=total)
                self.assertEqual(next(dispatcher)['local'],
                                 {'BrowsingUser': browsers, 'BookingUser': bookers})

    def test_cleanup_runs_when_payment_page_fails(self):
        results = Page('<a href="/appartements/42/">Apartment</a>')
        form = Page('<input name="csrfmiddlewaretoken" value="token">')
        self.user.cleanup = True
        self.user.get_page = MagicMock(side_effect=[results, form, form, form, None, form])
        self.user.post_form = MagicMock(side_effect=['/paiements/reservation/73/', '/reservations/73/'])
        self.user.search_and_book()
        self.assertEqual(self.user.post_form.call_args.args[0], '/reservations/73/annuler/')
        self.assertEqual(self.user.post_form.call_args_list[0].args[3]['accepter_politiques'], 'on')


if __name__ == '__main__':
    unittest.main()
