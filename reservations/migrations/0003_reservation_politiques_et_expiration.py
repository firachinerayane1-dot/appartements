from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0002_reservation_numero_reservation'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='politiques_acceptees_le',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='statut',
            field=models.CharField(
                choices=[
                    ('EN_ATTENTE', 'En attente'),
                    ('CONFIRMEE', 'Confirmée'),
                    ('ANNULEE', 'Annulée'),
                    ('TERMINEE', 'Terminée'),
                    ('REJETEE', 'Rejetée'),
                    ('EXPIREE', 'Expirée'),
                ],
                default='EN_ATTENTE',
                max_length=20,
            ),
        ),
    ]
