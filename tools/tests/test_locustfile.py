"""Tests sans serveur ni accès à la base applicative."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from locust.env import Environment

from locustfile import Page, ProjectUser, read_accounts


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
