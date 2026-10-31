from decimal import Decimal

from django.conf import settings


CANCELLATION_SUMMARY = (
    "Annulation à plus de 72 heures de l’arrivée prévue : remboursement de 50 % des sommes versées, "
    "y compris dans les 48 heures suivant la réservation. À 72 heures ou moins de l’arrivée, "
    "aucun remboursement. Non-présentation (no-show) : aucun remboursement. "
    "Annulation imputable à une erreur de notre établissement : remboursement de 100 %, quel que soit le délai. "
    "Les délais sont calculés à partir de l’heure d’arrivée affichée, dans le fuseau Africa/Casablanca."
)

STAY_POLICIES = (
    ('Garantie', "Une garantie de {garantie} MAD est à remettre à l’arrivée sous forme d’espèces ou de pré-autorisation sur carte bancaire. Elle est restituée après vérification de l’état du logement et de ses équipements. Toute retenue doit être justifiée."),
    ('Attribution du logement', "La réservation porte sur le logement et les dates indiqués dans le récapitulatif. Tout changement de logement doit être proposé au client et accepté par celui-ci."),
    ('Départ tardif', "Tout départ tardif doit être convenu avec la résidence, sous réserve de disponibilité. Les frais éventuels sont communiqués et acceptés avant la prolongation."),
    ('Non-présentation', "En cas de non-présentation à la date d’arrivée sans annulation préalable, aucun remboursement n’est accordé, sauf droits impératifs applicables. Prévenez le support en cas d’arrivée tardive."),
)


def format_amount(amount):
    return f'{Decimal(amount):,.2f}'.replace(',', ' ').replace('.', ',')


def policies_context(reservation=None):
    guarantee = format_amount(settings.RAHAL_STAY_GUARANTEE_AMOUNT)
    booking_policies = (
        {'title': 'Blocage des dates pendant 24 heures', 'text': "En acceptant ces conditions et en soumettant votre réservation, vous bloquez le logement aux dates choisies pendant 24 heures. Sans validation par l’administration avant l’échéance affichée, la réservation expire et les dates redeviennent disponibles."},
        {'title': 'Virement et validation', 'text': "Effectuez le virement du montant total sur le compte indiqué, puis envoyez au support WhatsApp votre numéro de réservation et le reçu du paiement. Le support vous contacte pour vérifier les informations. La réservation est confirmée uniquement après vérification du paiement et validation par l’administration. L’envoi d’un reçu ne prolonge pas le délai de 24 heures."},
        {'title': 'Annulation et remboursement', 'text': CANCELLATION_SUMMARY},
        {'title': 'Demander un remboursement', 'text': "Avant l’heure d’arrivée prévue, vous pouvez annuler depuis votre réservation. Pour toute autre demande, contactez le support avec votre numéro de réservation. La date et l’heure de la demande font foi. Les pourcentages s’appliquent aux sommes effectivement reçues pour l’hébergement. Le support vérifie les justificatifs, confirme par écrit le montant et le délai de traitement, et organise le remboursement. Aucun remboursement bancaire automatique n’est effectué sur ce site."},
        {'title': 'Paiement reçu après expiration', 'text': "Ne payez plus après l’échéance affichée. Si vous avez déjà effectué un virement et que votre réservation expire avant sa validation, contactez immédiatement le support. Le paiement ne réactive pas automatiquement les dates. Si le séjour ne peut pas être confirmé, les sommes reçues pour ce séjour seront remboursées intégralement."},
        {'title': 'Modification, réclamation et droits du client', 'text': "Toute modification des dates ou du séjour reste soumise à disponibilité et à votre accord sur le nouveau tarif. Pour une réclamation ou une situation exceptionnelle, contactez le support en conservant votre numéro de réservation et vos justificatifs. Ces conditions s’appliquent sous réserve des dispositions impératives du droit applicable et ne limitent pas les droits légaux du consommateur."},
    )
    return {
        'booking_policies': booking_policies,
        'stay_policies': tuple({'title': title, 'text': text.format(garantie=guarantee)} for title, text in STAY_POLICIES),
        'guarantee': guarantee,
        'check_in': settings.RAHAL_STAY_CHECK_IN,
        'check_out': settings.RAHAL_STAY_CHECK_OUT,
    }
