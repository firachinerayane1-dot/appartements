import csv
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from .models import Utilisateur


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class LoadtestUserImportTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'users.csv'

    def run_import(self, rows):
        with self.path.open('w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['email', 'password'])
            writer.writerows(rows)
        output = StringIO()
        call_command('import_loadtest_users', csv_path=str(self.path), stdout=output)
        return output.getvalue()

    def test_creation_and_repeat_preserve_password_and_account(self):
        rows = [('charge101@example.test', 'secret-one'), ('charge102@example.test', 'secret-two')]
        self.assertIn('2 comptes créés', self.run_import(rows))
        user = Utilisateur.objects.get(email=rows[0][0])
        old_password = user.password
        self.assertTrue(user.check_password(rows[0][1]))
        self.assertEqual(user.role, Utilisateur.CLIENT_REGULIER)
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertIn('0 comptes créés', self.run_import(rows))
        user.refresh_from_db()
        self.assertEqual(user.password, old_password)
        self.assertEqual(Utilisateur.objects.count(), 2)

    def test_password_conflict_does_not_create_other_accounts(self):
        user = Utilisateur.objects.create_user(email='charge001@example.test', password='original')
        with self.assertRaises(CommandError):
            self.run_import([('charge101@example.test', 'new'), (user.email, 'different')])
        self.assertEqual(Utilisateur.objects.count(), 1)
        user.refresh_from_db()
        self.assertTrue(user.check_password('original'))

    def test_rejects_real_addresses_duplicates_and_empty_passwords(self):
        for rows in [[('real@example.com', 'x')], [('charge001@example.test', '')],
                     [('charge001@example.test', 'x'), ('CHARGE001@example.test', 'y')]]:
            with self.subTest(rows=rows), self.assertRaises(CommandError):
                self.run_import(rows)
        self.assertEqual(Utilisateur.objects.count(), 0)

    def test_existing_privileged_account_is_not_reused(self):
        user = Utilisateur.objects.create_superuser(email='charge001@example.test', password='original')
        with self.assertRaises(CommandError):
            self.run_import([(user.email, 'original')])
