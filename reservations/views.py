from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.mixins import administrateur_required
from apartments.models import Appartement
from services.reservation_services import creer_reservation
from .forms import FiltreReservationAdminForm, ReservationForm
from .models import Reservation


@login_required
def reserver(request, appartement_id):
    appartement = get_object_or_404(Appartement, pk=appartement_id, disponible=True)
    form = ReservationForm(request.POST or None, initial={'date_debut': request.GET.get('date_debut'), 'date_fin': request.GET.get('date_fin')})
    if request.method == 'POST' and form.is_valid():
        try:
            reservation = creer_reservation(request.user, appartement, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
        else:
            messages.success(request, "Réservation créée. Procédez maintenant au paiement.")
            return redirect('payments:payer', reservation_id=reservation.pk)
    return render(request, 'reservations/reserver.html', {'form': form, 'appartement': appartement})


@login_required
def mes_reservations(request):
    reservations = request.user.reservations.select_related('appartement')
    return render(request, 'reservations/mes_reservations.html', {'reservations': reservations})


@login_required
def detail(request, pk):
    queryset = Reservation.objects.select_related('appartement', 'client')
    if not request.user.est_administrateur():
        queryset = queryset.filter(client=request.user)
    reservation = get_object_or_404(queryset, pk=pk)
    return render(request, 'reservations/detail.html', {'reservation': reservation, 'recap': reservation.generer_recap()})


@login_required
@require_POST
def annuler(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk, client=request.user)
    reservation.annuler()
    messages.success(request, "La réservation a été annulée.")
    return redirect('reservations:detail', pk=pk)


@administrateur_required
def admin_liste(request):
    form = FiltreReservationAdminForm(request.GET or None)
    reservations = Reservation.objects.select_related('client', 'appartement')
    if form.is_valid():
        if form.cleaned_data.get('statut'):
            reservations = reservations.filter(statut=form.cleaned_data['statut'])
        if form.cleaned_data.get('appartement'):
            reservations = reservations.filter(appartement=form.cleaned_data['appartement'])
        if form.cleaned_data.get('date_debut'):
            reservations = reservations.filter(date_fin__gt=form.cleaned_data['date_debut'])
        if form.cleaned_data.get('date_fin'):
            reservations = reservations.filter(date_debut__lt=form.cleaned_data['date_fin'])
    return render(request, 'reservations/admin_liste.html', {'form': form, 'reservations': reservations})


@administrateur_required
@require_POST
def admin_annuler(request, pk):
    get_object_or_404(Reservation, pk=pk).annuler()
    messages.success(request, "Réservation annulée.")
    return redirect('reservations:admin_liste')


@administrateur_required
@require_POST
def admin_supprimer(request, pk):
    get_object_or_404(Reservation, pk=pk).delete()
    messages.success(request, "Réservation supprimée.")
    return redirect('reservations:admin_liste')
