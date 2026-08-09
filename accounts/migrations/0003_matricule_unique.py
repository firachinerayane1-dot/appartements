from django.db import migrations, models


def normaliser_et_verifier_les_matricules(apps, schema_editor):
    Utilisateur = apps.get_model('accounts', 'Utilisateur')
    vus = {}
    for utilisateur in Utilisateur.objects.exclude(matricule__isnull=True).iterator():
        matricule = (utilisateur.matricule or '').strip() or None
        if matricule is not None and matricule in vus:
            raise RuntimeError(
                "Impossible de rendre les numéros d'adhérent uniques : "
                f"le matricule {matricule!r} appartient aux utilisateurs "
                f"{vus[matricule]} et {utilisateur.pk}."
            )
        if matricule is not None:
            vus[matricule] = utilisateur.pk
        if utilisateur.matricule != matricule:
            Utilisateur.objects.filter(pk=utilisateur.pk).update(matricule=matricule)


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_client_fm6_et_consentement'),
    ]

    operations = [
        migrations.RunPython(
            normaliser_et_verifier_les_matricules,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='utilisateur',
            name='matricule',
            field=models.CharField(
                blank=True,
                error_messages={'unique': "Ce numéro d'adhérent est déjà utilisé."},
                max_length=50,
                null=True,
                unique=True,
            ),
        ),
    ]
