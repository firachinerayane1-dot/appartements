"""Synthetic index benchmark using only a disposable in-memory SQLite database."""
import os
import sys
from datetime import date
sys.path.insert(0, os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'webbap.settings'
import django
from django.conf import settings
settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
django.setup()
from django.core.management import call_command
from django.db import connection
from accounts.models import Utilisateur
from apartments.models import Appartement, Photo, PeriodeVacances
from reservations.models import Reservation
from notifications.models import Notification
call_command('migrate', verbosity=0)
users = Utilisateur.objects.bulk_create([Utilisateur(email=f'bench{i}@example.test') for i in range(100)])
apts = Appartement.objects.bulk_create([Appartement(titre=f'Appartement {i:04}', description='Test') for i in range(200)])
Photo.objects.bulk_create([Photo(appartement=a, image=f'photo{i}.jpg', principale=i==15) for a in apts for i in range(20)])
Reservation.objects.bulk_create([Reservation(client=users[i%100], appartement=apts[i%200], date_debut=date(2027,1,1), date_fin=date(2027,1,2), montant_total=700, statut='EN_ATTENTE' if i%3 else 'CONFIRMEE') for i in range(20000)])
Notification.objects.bulk_create([Notification(client=users[i%100], message='Test', lue=bool(i%3)) for i in range(20000)])
models = [Appartement, Photo, PeriodeVacances, Reservation, Notification]
with connection.schema_editor() as editor:
    for model in models:
        for index in model._meta.indexes:
            editor.remove_index(model, index)
print('BEFORE')
call_command('profile_queries', client_id=users[0].pk, repeat=10, date_debut=date(2027, 1, 1), date_fin=date(2027, 1, 2))
with connection.schema_editor() as editor:
    for model in models:
        for index in model._meta.indexes:
            editor.add_index(model, index)
print('AFTER')
call_command('profile_queries', client_id=users[0].pk, repeat=10, date_debut=date(2027, 1, 1), date_fin=date(2027, 1, 2))
