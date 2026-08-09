import decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('apartments', '0002_tarif_regulier_700'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appartement',
            name='prix_par_nuit',
            field=models.DecimalField(
                decimal_places=2,
                default=decimal.Decimal('700.00'),
                max_digits=10,
                verbose_name='tarif client régulier par nuit',
            ),
        ),
        migrations.AddField(
            model_name='appartement',
            name='prix_fm6_par_nuit',
            field=models.DecimalField(
                decimal_places=2,
                default=decimal.Decimal('500.00'),
                max_digits=10,
                verbose_name='tarif client FM6 par nuit',
            ),
        ),
    ]
