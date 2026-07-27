import secrets
import string

import django.core.validators
from django.db import migrations, models

import reservations.models


def generer_numero_existant(numeros_utilises):
    while True:
        numero = (
            ''.join(secrets.choice(string.ascii_lowercase) for _ in range(2))
            + ''.join(secrets.choice(string.ascii_uppercase) for _ in range(2))
            + ''.join(secrets.choice(string.digits) for _ in range(5))
        )
        if numero not in numeros_utilises:
            return numero


def remplir_numeros_reservation(apps, schema_editor):
    Reservation = apps.get_model('reservations', 'Reservation')
    numeros_utilises = set()

    for reservation in Reservation.objects.filter(numero_reservation__isnull=True).iterator():
        numero = generer_numero_existant(numeros_utilises)
        Reservation.objects.filter(pk=reservation.pk).update(numero_reservation=numero)
        numeros_utilises.add(numero)


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='numero_reservation',
            field=models.CharField(editable=False, max_length=9, null=True),
        ),
        migrations.RunPython(remplir_numeros_reservation, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='reservation',
            name='numero_reservation',
            field=models.CharField(
                default=reservations.models.generer_numero_reservation,
                editable=False,
                max_length=9,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message='Le numéro de réservation doit contenir 2 lettres minuscules, '
                                '2 lettres majuscules et 5 chiffres.',
                        regex='^[a-z]{2}[A-Z]{2}\\d{5}$',
                    ),
                ],
            ),
        ),
    ]
