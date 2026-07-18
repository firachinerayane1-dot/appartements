from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from accounts.mixins import administrateur_required
from reservations.models import Reservation
from .forms import PaiementForm
from .models import Paiement


@login_required
def payer(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id, client=request.user)
    if reservation.statut != Reservation.EN_ATTENTE:
        messages.info(request, "Cette réservation n'est plus en attente de paiement.")
        return redirect('reservations:detail', pk=reservation.pk)
    form = PaiementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            paiement = reservation.generer_paiement(form.cleaned_data['methode'])
            paiement.effectuer()
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
        else:
            messages.success(request, "Paiement simulé avec succès.")
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
