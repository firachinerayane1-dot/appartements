"""Traitement hors requête HTTP de la file des confirmations."""
import logging
from datetime import timedelta
from uuid import uuid4

from django.db.models import F
from django.utils import timezone

from payments.models import ConfirmationEmail
from services.confirmation_reservation import envoyer_email_confirmation

logger = logging.getLogger(__name__)


def traiter_confirmations(limite=100):
    envoyes = erreurs = 0
    maintenant = timezone.now()
    ids = list(ConfirmationEmail.objects.filter(
        envoye_le__isnull=True, disponible_le__lte=maintenant,
    ).values_list('pk', flat=True)[:limite])
    for pk in ids:
        jeton = uuid4()
        # Prise atomique compatible SQLite/PostgreSQL. Le bail permet la reprise
        # après l'arrêt brutal d'un worker, sans transaction ouverte pendant SMTP.
        pris = ConfirmationEmail.objects.filter(
            pk=pk, envoye_le__isnull=True, disponible_le__lte=timezone.now(),
        ).update(verrou=jeton, disponible_le=timezone.now() + timedelta(minutes=15),
                 tentatives=F('tentatives') + 1)
        if not pris:
            continue
        tache = ConfirmationEmail.objects.select_related(
            'paiement__reservation__client', 'paiement__reservation__appartement',
        ).get(pk=pk)
        possedee = ConfirmationEmail.objects.filter(pk=pk, verrou=jeton)
        try:
            if envoyer_email_confirmation(tache.paiement) != 1:
                raise RuntimeError("Le serveur email n'a accepté aucun message.")
        except Exception as exc:
            logger.exception('Échec de la confirmation email %s', pk)
            possedee.update(
                verrou=None, derniere_erreur=type(exc).__name__,
                disponible_le=timezone.now() + timedelta(minutes=min(2 ** min(tache.tentatives, 10), 60)),
            )
            erreurs += 1
        else:
            possedee.update(envoye_le=timezone.now(), verrou=None, derniere_erreur='')
            envoyes += 1
    return envoyes, erreurs
