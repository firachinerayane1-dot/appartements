"""Import dedicated Locust accounts without resetting existing credentials."""
import csv
import re

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Crée les comptes chargeNNN@example.test du CSV Locust, sans modifier les comptes existants.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', default='loadtest-users.csv', dest='csv_path')

    def handle(self, *args, **options):
        try:
            with open(options['csv_path'], newline='', encoding='utf-8-sig') as source:
                rows = list(csv.DictReader(source))
        except (OSError, UnicodeError, csv.Error) as exc:
            raise CommandError('Impossible de lire le CSV de comptes.') from exc
        if not rows:
            raise CommandError('Le CSV est vide.')
        seen = set()
        for row in rows:
            email = (row.get('email') or '').strip().lower()
            if not re.fullmatch(r'charge\d+@example\.test', email) or not row.get('password'):
                raise CommandError('Chaque ligne doit contenir email,password et un email chargeNNN@example.test.')
            if email in seen:
                raise CommandError('Le CSV contient des comptes en double.')
            seen.add(email)
            row['email'] = email

        User = get_user_model()
        created = 0
        with transaction.atomic():
            existing = {user.email: user for user in User.objects.filter(email__in=seen)}
            # Validate every collision before creating anything; never reset a password.
            for row in rows:
                user = existing.get(row['email'])
                if user is not None and (
                    not user.is_active or user.is_staff or user.is_superuser
                    or user.role != User.CLIENT_REGULIER
                    or not user.check_password(row['password'])
                ):
                    raise CommandError(f"Compte existant incompatible : {row['email']}. Aucun compte modifié.")
            for row in rows:
                if row['email'] not in existing:
                    User.objects.create_user(
                        email=row['email'], password=row['password'],
                        nom='Charge', prenom=row['email'].split('@')[0],
                        role=User.CLIENT_REGULIER,
                    )
                    created += 1
        self.stdout.write(self.style.SUCCESS(
            f'{created} comptes créés ; {len(rows) - created} comptes existants vérifiés ; {len(rows)} comptes prêts.'
        ))
