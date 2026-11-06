"""Parcours HTTP connexion → recherche → réservation. Voir docs/test-charge.md."""
import csv
import os
import random
import re
from datetime import datetime, timedelta
from html.parser import HTMLParser
from queue import Empty, Queue
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from locust import HttpUser, between, events, task
from locust.exception import StopUser
from locust.runners import MasterRunner


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.csrf = None
        self.apartments = set()
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('name') == 'csrfmiddlewaretoken':
            self.csrf = attrs.get('value')
        if tag == 'a':
            href = attrs.get('href', '')
            # Only application-relative apartment links, never external destinations.
            match = re.fullmatch(r'/appartements/(\d+)/', urlsplit(href).path)
            if match and href.startswith('/') and not href.startswith('//'):
                self.apartments.add(int(match[1]))


def read_accounts(path):
    with open(path, newline='', encoding='utf-8-sig') as source:
        rows = list(csv.DictReader(source))
    if not rows or any(not row.get('email') or not row.get('password') for row in rows):
        raise ValueError('Le CSV doit contenir email,password et au moins un compte.')
    if len({row['email'].strip().lower() for row in rows}) != len(rows):
        raise ValueError('Chaque compte du CSV doit être unique.')
    return rows


@events.test_start.add_listener
def prepare_accounts(environment, **kwargs):
    if isinstance(environment.runner, MasterRunner):
        return
    pool = Queue()
    for row in read_accounts(os.environ.get('LOADTEST_USERS_CSV', 'loadtest-users.csv')):
        pool.put(row)
    environment.loadtest_accounts = pool


class ProjectUser(HttpUser):
    wait_time = between(2, 6)

    def on_start(self):
        self.account = None
        self.cleanup = os.environ.get('LOADTEST_CANCEL', '0') == '1'
        try:
            self.account = self.environment.loadtest_accounts.get_nowait()
        except Empty:
            self.environment.events.request.fire(
                request_type='CONFIG', name='Comptes disponibles', response_time=0,
                response_length=0, exception=RuntimeError('Pas assez de comptes CSV'),
            )
            raise StopUser()

    def on_stop(self):
        if self.account:
            self.environment.loadtest_accounts.put(self.account)
            self.account = None

    def get_page(self, path, name, params=None, csrf=False):
        with self.client.get(path, params=params, name=name, catch_response=True,
                             allow_redirects=False, timeout=30) as response:
            if response.status_code != 200:
                response.failure(f'Page attendue HTTP 200, reçu {response.status_code}')
                return None
            page = Page(response.text)
            if csrf and not page.csrf:
                response.failure('Formulaire CSRF absent')
                return None
            return page

    def post_form(self, path, name, page, data, expected):
        with self.client.post(
            path, name=name,
            data={**data, 'csrfmiddlewaretoken': page.csrf},
            headers={'Referer': urljoin(self.host, path)},
            allow_redirects=False, catch_response=True, timeout=30,
        ) as response:
            location = response.headers.get('Location', '')
            destination = urlsplit(urljoin(self.host, location))
            origin = urlsplit(self.host)
            if (response.status_code != 302 or not location
                    or (destination.scheme, destination.netloc) != (origin.scheme, origin.netloc)
                    or not re.fullmatch(expected, destination.path)):
                # A Django form can return 200 even when the operation failed.
                response.failure(f'Formulaire refusé ou redirection inattendue (HTTP {response.status_code})')
                return None
            return destination.path

    @staticmethod
    def dates():
        today = datetime.now(ZoneInfo('Africa/Casablanca')).date()
        while True:
            start = today + timedelta(days=random.randint(7, 365))
            nights = random.randint(2, 5)
            # August is restricted to FM6; use dates valid for both client types.
            if all((start + timedelta(days=n)).month != 8 for n in range(nights)):
                return {'date_debut': start.isoformat(),
                        'date_fin': (start + timedelta(days=nights)).isoformat()}

    @task
    def reservation_journey(self):
        # Each loop represents a fresh visit, including the cost of authentication.
        self.client.cookies.clear()
        if self.get_page('/', '01 Accueil') is None:
            return
        self.wait()
        login = self.get_page('/accounts/connexion/', '02 Formulaire connexion', csrf=True)
        if login is None:
            return
        self.wait()
        if not self.post_form('/accounts/connexion/', '03 Connexion', login, {
            'username': self.account['email'], 'password': self.account['password'],
            'next': '/accounts/profil/',
        }, r'/accounts/profil/'):
            return
        if self.get_page('/accounts/profil/', '04 Profil authentifié') is None:
            return
        self.wait()
        try:
            self.search_and_book()
        finally:
            page = self.get_page('/accounts/profil/', '15 Profil avant déconnexion', csrf=True)
            if page:
                self.post_form('/accounts/deconnexion/', '16 Déconnexion', page, {},
                               r'/accounts/connexion/')

    def search_and_book(self):
        for attempt in range(3):
            dates = self.dates()
            results = self.get_page('/appartements/', '05 Recherche disponibilités', dates)
            if results is None:
                return
            self.wait()
            if results.apartments:
                break
        else:
            self.environment.events.request.fire(
                request_type='BUSINESS', name='Aucun logement après 3 recherches',
                response_time=0, response_length=0,
                exception=RuntimeError('Stock indisponible : vérifier les données de test'),
            )
            return

        candidates = random.sample(sorted(results.apartments),
                                   k=min(len(results.apartments), random.randint(1, 3)))
        for apartment_id in candidates:
            if self.get_page(f'/appartements/{apartment_id}/', '06 Détail appartement', dates) is None:
                return
            self.wait()
        booking_path = f'/reservations/appartement/{apartment_id}/reserver/'
        form = self.get_page(booking_path, '07 Formulaire réservation', dates, csrf=True)
        if form is None:
            return
        self.wait()
        if self.get_page('/reservations/politiques/', '08 Lecture conditions') is None:
            return
        self.wait()
        payment_path = self.post_form(booking_path, '09 Création réservation', form,
                                     {**dates, 'accepter_politiques': 'on'},
                                     r'/paiements/reservation/\d+/')
        if not payment_path:
            return
        reservation_id = payment_path.rstrip('/').split('/')[-1]
        detail_path = f'/reservations/{reservation_id}/'
        try:
            if self.get_page(payment_path, '10 Instructions de virement') is None:
                return
            self.wait()
            if self.get_page('/reservations/mes-reservations/', '11 Mes réservations') is None:
                return
            self.wait()
            self.get_page(detail_path, '12 Détail réservation')
        finally:
            if self.cleanup:
                page = self.get_page(detail_path, '13 Formulaire annulation', csrf=True)
                if page:
                    self.post_form(f'{detail_path}annuler/', '14 Annulation de test', page, {},
                                   re.escape(detail_path))
