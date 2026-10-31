import logging
import re
from urllib.parse import urlencode

from django.conf import settings
from django.views.decorators.http import require_http_methods

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.mixins import administrateur_required
from reservations.models import Reservation
from services.confirmation_reservation import envoyer_email_confirmation
from .forms import ValidationVirementForm
from .models import Paiement


logger = logging.getLogger(__name__)


@login_required
@require_http_methods(['GET'])
def payer(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id, client=request.user)
    if reservation.expirer_si_necessaire():
        messages.error(
            request,
            "Le délai de paiement de 24 heures est expiré. L'appartement est de nouveau disponible.",
        )
        return redirect('reservations:detail', pk=reservation.pk)
    if reservation.statut != Reservation.EN_ATTENTE:
        messages.info(request, "Cette réservation n'est plus en attente de paiement.")
        return redirect('reservations:detail', pk=reservation.pk)
    if not reservation.politiques_acceptees_le:
        messages.info(request, "Vous devez lire et accepter les politiques avant d'accéder au paiement.")
        return redirect('reservations:politiques', pk=reservation.pk)
    banque = {
        'nom': settings.PAYMENT_BANK_NAME,
        'titulaire': settings.PAYMENT_ACCOUNT_HOLDER,
        'rib': settings.PAYMENT_RIB,
        'iban': settings.PAYMENT_IBAN,
        'bic': settings.PAYMENT_BIC,
    }
    numero = re.sub(r'[ +().-]', '', settings.SUPPORT_WHATSAPP_NUMBER)
    whatsapp_url = ''
    if re.fullmatch(r'[1-9][0-9]{7,14}', numero):
        message = f"Bonjour, voici ma réservation {reservation.numero_reservation} pour {reservation.appartement}, du {reservation.date_debut:%d/%m/%Y} au {reservation.date_fin:%d/%m/%Y}, d’un montant de {reservation.montant_total} MAD. Je vous joins mon reçu de virement pour vérification et confirmation."
        whatsapp_url = f"https://wa.me/{numero}?{urlencode({'text': message})}"
    return render(request, 'payments/payer.html', {
        'reservation': reservation, 'banque': banque,
        'banque_configuree': all((banque['nom'], banque['titulaire'], banque['rib'])),
        'whatsapp_url': whatsapp_url, 'contact_email': settings.RAHAL_STAY_CONTACT_EMAIL,
    })


@administrateur_required
@require_http_methods(['GET', 'POST'])
def admin_valider(request, reservation_id):
    reservation = get_object_or_404(Reservation.objects.select_related('client', 'appartement'), pk=reservation_id)
    reservation.expirer_si_necessaire()
    if reservation.statut != Reservation.EN_ATTENTE or not reservation.politiques_acceptees_le:
        messages.error(request, "Cette réservation n’est pas éligible à la validation. Vérifiez son statut et l’acceptation des politiques.")
        return redirect('reservations:admin_liste')
    form = ValidationVirementForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            paiement = reservation.generer_paiement(Paiement.VIREMENT)
            paiement.effectuer(administrateur=request.user, reference=form.cleaned_data['reference_virement'])
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
        else:
            if paiement.validation_nouvelle:
                try:
                    envoyer_email_confirmation(paiement)
                except Exception:
                    logger.exception("Échec de la confirmation pour %s", reservation.numero_reservation)
                    messages.warning(request, "Réservation validée, mais l’email de confirmation n’a pas pu être envoyé. Le reçu reste disponible au client.")
                else:
                    messages.success(request, "Virement validé et réservation confirmée. La confirmation et son PDF ont été envoyés au client.")
            return redirect('reservations:admin_liste')
    return render(request, 'payments/admin_valider.html', {'form': form, 'reservation': reservation})


@login_required
def recu(request, pk):
    paiement = get_object_or_404(Paiement.objects.select_related('reservation__client'), pk=pk, reservation__client=request.user, statut=Paiement.PAYE)
    return render(request, 'payments/recu.html', {'paiement': paiement, 'recu': paiement.get_recu()})


@administrateur_required
def admin_liste(request):
    paiements = Paiement.objects.select_related('reservation__client', 'reservation__appartement')
    if request.GET.get('statut'):
        paiements = paiements.filter(statut=request.GET['statut'])
    if request.GET.get('methode'):
        paiements = paiements.filter(methode=request.GET['methode'])
    if request.GET.get('date'):
        paiements = paiements.filter(date_paiement__date=request.GET['date'])
    return render(request, 'payments/admin_liste.html', {'paiements': paiements, 'statuts': Paiement.STATUTS, 'methodes': Paiement.METHODES})
