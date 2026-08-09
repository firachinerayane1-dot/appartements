from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='utilisateur',
            name='consentement_donnees_le',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='utilisateur',
            name='role',
            field=models.CharField(
                choices=[
                    ('CLIENT_REGULIER', 'Client Régulier'),
                    ('ENSEIGNANT', 'Client FM6'),
                    ('ADMINISTRATEUR', 'Administrateur'),
                ],
                default='CLIENT_REGULIER',
                max_length=20,
            ),
        ),
    ]
