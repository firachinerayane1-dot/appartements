import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.mixins import administrateur_required
from reservations.models import Reservation
from services.confirmation_reservation import envoyer_email_confirmation
from .forms import PaiementForm
from .models import Paiement


logger = logging.getLogger(__name__)


@login_required
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
    form = PaiementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            paiement = reservation.generer_paiement(Paiement.CARTE)
            paiement.effectuer()
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
        else:
            try:
                envoyer_email_confirmation(paiement)
            except Exception:
                logger.exception(
                    "Échec de l'envoi de la confirmation pour la réservation %s",
                    reservation.numero_reservation,
                )
                messages.warning(
                    request,
                    "Paiement confirmé, mais l'e-mail de confirmation n'a pas pu être envoyé. "
                    "Votre reçu reste disponible.",
                )
            else:
                messages.success(
                    request,
                    "Paiement confirmé. La confirmation et son PDF ont été envoyés par e-mail.",
                )
            return redirect('payments:recu', pk=paiement.pk)
    return render(request, 'payments/payer.html', {'form': form, 'reservation': reservation})


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
