from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef

from apartments.models import Appartement
from reservations.models import Reservation


@transaction.atomic
def creer_reservation(client, appartement, date_debut, date_fin):
    """Point d'entrée unique appliquant disponibilité et priorité enseignant."""
    if not client.is_authenticated or client.est_administrateur():
        raise PermissionDenied("Seul un client peut réserver.")

    appartement = Appartement.objects.select_for_update().get(pk=appartement.pk)
    if not appartement.is_disponible(date_debut, date_fin):
        raise ValidationError("Cet appartement n'est pas disponible aux dates choisies.")

    vacances = appartement.periodes_vacances.all()
    if any(periode.chevauche(date_debut, date_fin) for periode in vacances) and not client.est_enseignant():
        raise ValidationError("Cet appartement n'est disponible qu'aux enseignants pendant cette période.")

    reservation = Reservation(
        client=client,
        appartement=appartement,
        date_debut=date_debut,
        date_fin=date_fin,
        statut=Reservation.EN_ATTENTE,
        montant_total=appartement.calculer_prix(date_debut, date_fin, client),
    )
    reservation.full_clean()
    reservation.save()
    return reservation


def chercher_appartements_disponibles(date_debut, date_fin, client=None):
    """Retourne les appartements libres pendant toute la période demandée.

    Les bornes sont semi-ouvertes (date_debut incluse, date_fin exclue) : un
    départ le jour d'une nouvelle arrivée ne constitue donc pas un conflit.
    """
    reservations_en_conflit = Reservation.objects.filter(
        appartement_id=OuterRef('pk'),
        statut__in=(Reservation.EN_ATTENTE, Reservation.CONFIRMEE),
        date_debut__lt=date_fin,
        date_fin__gt=date_debut,
    )
    appartements = (
        Appartement.objects.filter(disponible=True)
        .annotate(a_une_reservation_en_conflit=Exists(reservations_en_conflit))
        .filter(a_une_reservation_en_conflit=False)
    )

    # Cette règle métier existe déjà dans l'application : pendant les
    # vacances, certains appartements sont réservés aux enseignants.
    if client and client.is_authenticated and not client.est_enseignant():
        periodes_vacances_en_conflit = appartement_periodes_vacances(date_debut, date_fin)
        appartements = (
            appartements
            .annotate(a_une_periode_vacances=Exists(periodes_vacances_en_conflit))
            .filter(a_une_periode_vacances=False)
        )

    return appartements


def appartement_periodes_vacances(date_debut, date_fin):
    """Construit la sous-requête des vacances qui chevauchent une période."""
    from apartments.models import PeriodeVacances

    return PeriodeVacances.objects.filter(
        appartement_id=OuterRef('pk'),
        date_debut__lt=date_fin,
        date_fin__gt=date_debut,
    )
