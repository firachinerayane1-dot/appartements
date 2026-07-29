from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paiement',
            name='methode',
            field=models.CharField(
                choices=[('CARTE', 'Carte bancaire')],
                max_length=20,
            ),
        ),
    ]
