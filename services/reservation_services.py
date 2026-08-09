from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from apartments.models import Appartement
from reservations.models import Reservation


MESSAGE_AOUT_RESERVE_FM6 = "Le mois d'août est réservé aux clients FM6."


def chevauche_le_mois_aout(date_debut, date_fin):
    """Indique si le séjour semi-ouvert contient au moins une nuit en août."""
    if not date_debut or not date_fin or date_fin <= date_debut:
        return False
    for annee in range(date_debut.year, date_fin.year + 1):
        debut_aout = date(annee, 8, 1)
        debut_septembre = date(annee, 9, 1)
        if date_debut < debut_septembre and date_fin > debut_aout:
            return True
    return False


def _verrouiller_client(client):
    """Sérialise toutes les écritures de réservation d'un même adhérent."""
    return get_user_model().objects.select_for_update().get(pk=client.pk)


def _verrouiller_appartements(*appartement_ids):
    ids = sorted({pk for pk in appartement_ids if pk is not None})
    return {
        appartement.pk: appartement
        for appartement in Appartement.objects.select_for_update().filter(pk__in=ids).order_by('pk')
    }


@transaction.atomic
def creer_reservation(client, appartement, date_debut, date_fin):
    """Point d'entrée unique appliquant les règles de disponibilité."""
    if not client.is_authenticated or client.est_administrateur():
        raise PermissionDenied("Seul un client peut réserver.")
    if not client.est_client_fm6() and chevauche_le_mois_aout(date_debut, date_fin):
        raise ValidationError(MESSAGE_AOUT_RESERVE_FM6)

    client = _verrouiller_client(client)
    appartement = _verrouiller_appartements(appartement.pk)[appartement.pk]

    # Les attentes périmées ne participent plus ni à la disponibilité du
    # logement, ni aux conflits de l'adhérent.
    Reservation.objects.filter(
        client=client,
        statut=Reservation.EN_ATTENTE,
        date_reservation__lte=timezone.now() - Reservation.DELAI_PAIEMENT,
    ).update(statut=Reservation.EXPIREE)

    reservation = Reservation(
        client=client,
        appartement=appartement,
        date_debut=date_debut,
        date_fin=date_fin,
        statut=Reservation.EN_ATTENTE,
        montant_total=appartement.calculer_prix(date_debut, date_fin, client),
    )
    reservation.full_clean()

    if not appartement.is_disponible(date_debut, date_fin):
        raise ValidationError("Cet appartement n'est pas disponible aux dates choisies.")

    reservation.save()
    return reservation


@transaction.atomic
def modifier_reservation(reservation, *, date_debut, date_fin, appartement=None):
    """Modifie les dates/logement en appliquant les mêmes règles que la création."""
    client = _verrouiller_client(reservation.client)
    if not client.est_client_fm6() and chevauche_le_mois_aout(date_debut, date_fin):
        raise ValidationError(MESSAGE_AOUT_RESERVE_FM6)
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    appartement_id = appartement.pk if appartement is not None else reservation.appartement_id
    appartements = _verrouiller_appartements(reservation.appartement_id, appartement_id)
    appartement = appartements[appartement_id]

    Reservation.objects.filter(
        client=client,
        statut=Reservation.EN_ATTENTE,
        date_reservation__lte=timezone.now() - Reservation.DELAI_PAIEMENT,
    ).exclude(pk=reservation.pk).update(statut=Reservation.EXPIREE)

    reservation.client = client
    reservation.appartement = appartement
    reservation.date_debut = date_debut
    reservation.date_fin = date_fin
    reservation.montant_total = appartement.calculer_prix(date_debut, date_fin, client)
    reservation.full_clean()

    if not appartement.is_disponible(
        date_debut,
        date_fin,
        exclude_reservation=reservation.pk,
    ):
        raise ValidationError("Cet appartement n'est pas disponible aux dates choisies.")

    reservation.save(update_fields=('appartement', 'date_debut', 'date_fin', 'montant_total'))
    return reservation


def chercher_appartements_disponibles(date_debut, date_fin, client=None):
    """Retourne les appartements libres pendant toute la période demandée.

    Les bornes sont semi-ouvertes (date_debut incluse, date_fin exclue) : un
    départ le jour d'une nouvelle arrivée ne constitue donc pas un conflit.
    """
    est_client_fm6 = (
        client
        and getattr(client, 'is_authenticated', False)
        and client.est_client_fm6()
    )
    if chevauche_le_mois_aout(date_debut, date_fin) and not est_client_fm6:
        return Appartement.objects.none()

    reservations_en_conflit = Reservation.objects.filter(
        Q(statut=Reservation.CONFIRMEE)
        | Q(
            statut=Reservation.EN_ATTENTE,
            date_reservation__gt=timezone.now() - timedelta(hours=24),
        ),
        appartement_id=OuterRef('pk'),
        date_debut__lt=date_fin,
        date_fin__gt=date_debut,
    )
    appartements = Appartement.objects.filter(
        ~Exists(reservations_en_conflit),
        disponible=True,
    )

    return appartements
