import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0001_initial'),
        ('reservations', '0003_reservation_politiques_et_expiration'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='categorie',
            field=models.CharField(
                choices=[
                    ('INFORMATION', 'Information'),
                    ('EXPIRATION_RESERVATION', 'Expiration de réservation'),
                ],
                default='INFORMATION',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='reservation',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='notifications',
                to='reservations.reservation',
            ),
        ),
        migrations.AddConstraint(
            model_name='notification',
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ('categorie', 'EXPIRATION_RESERVATION'),
                    ('reservation__isnull', False),
                ),
                fields=('reservation', 'categorie'),
                name='notification_expiration_reservation_unique',
            ),
        ),
    ]
