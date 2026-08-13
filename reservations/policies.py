from decimal import Decimal

from django.conf import settings


STAY_POLICIES = (
    (
        'Garantie',
        "Une garantie de {garantie} MAD est à remettre à l’arrivée sous forme "
        "d’espèces ou de pré-autorisation sur carte bancaire. Elle est restituée "
        "après vérification de l’état du logement et de ses équipements.",
    ),
    (
        'Attribution du logement',
        "L’attribution du logement s’effectue le jour de l’arrivée selon les "
        "disponibilités et l’organisation de la résidence.",
    ),
    (
        'Départ tardif',
        "Tout logement non libéré à partir de l’heure de départ est facturé à 50 % "
        "au titre du Day-Use. Au-delà de 15 h, une nuit complète peut être facturée.",
    ),
    (
        'Non-présentation',
        "En cas de non-présentation, la réservation reste non modifiable, non "
        "annulable et non remboursable.",
    ),
)


def format_amount(amount):
    return f'{Decimal(amount):,.2f}'.replace(',', ' ').replace('.', ',')


def policies_context(reservation):
    guarantee = format_amount(settings.RAHAL_STAY_GUARANTEE_AMOUNT)
    booking_policies = (
        {
            'title': 'Maintien de la réservation',
            'text': (
                "L’appartement est maintenu pendant 24 heures à compter de la création "
                f"de la réservation, soit jusqu’au {reservation.date_expiration:%d/%m/%Y à %H:%M}. "
                "Sans paiement avant cette échéance, la réservation expire et le logement "
                "redevient disponible."
            ),
        },
        {
            'title': 'Paiement et confirmation',
            'text': (
                "Le paiement est disponible uniquement par carte bancaire. Le paiement "
                "confirme définitivement la réservation."
            ),
        },
        {
            'title': 'Annulation et remboursement',
            'text': (
                "Avant le paiement, la demande peut être annulée. Après le paiement, la "
                "réservation ne peut plus être annulée et le tarif payé est non remboursable."
            ),
        },
    )
    stay_policies = tuple(
        {'title': title, 'text': text.format(garantie=guarantee)}
        for title, text in STAY_POLICIES
    )
    return {
        'booking_policies': booking_policies,
        'stay_policies': stay_policies,
        'guarantee': guarantee,
        'check_in': settings.RAHAL_STAY_CHECK_IN,
        'check_out': settings.RAHAL_STAY_CHECK_OUT,
    }
