import decimal

from django.db import migrations, models


def fixer_tarif_regulier(apps, schema_editor):
    Appartement = apps.get_model('apartments', 'Appartement')
    Appartement.objects.update(prix_par_nuit=decimal.Decimal('700.00'))


class Migration(migrations.Migration):
    dependencies = [
        ('apartments', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(fixer_tarif_regulier, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='appartement',
            name='prix_par_nuit',
            field=models.DecimalField(
                decimal_places=2,
                default=decimal.Decimal('700.00'),
                editable=False,
                max_digits=10,
            ),
        ),
    ]
