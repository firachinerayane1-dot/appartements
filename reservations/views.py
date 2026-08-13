import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from accounts.mixins import administrateur_required
from apartments.models import Appartement, Photo
from services.reservation_services import creer_reservation
from .forms import FiltreReservationAdminForm, ReservationForm
from .models import Reservation


logger = logging.getLogger(__name__)


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
            lien_politiques = request.build_absolute_uri(
                reverse('reservations:politiques', args=(reservation.pk,))
            )
            try:
                reservation.envoyer_email_politiques(lien_politiques)
            except Exception:
                logger.exception(
                    "Échec de l'envoi des politiques pour la réservation %s",
                    reservation.numero_reservation,
                )
                messages.warning(
                    request,
                    "La réservation est créée, mais l'e-mail n'a pas pu être envoyé. "
                    "Vous pouvez consulter les politiques depuis cette page.",
                )
            else:
                messages.success(
                    request,
                    "Réservation créée. Consultez votre e-mail et acceptez les politiques "
                    "dans les 24 heures pour accéder au paiement.",
                )
            return redirect('reservations:detail', pk=reservation.pk)
    return render(
        request,
        'reservations/reserver.html',
        {
            'form': form,
            'appartement': appartement,
            'tarif_nuit': appartement.tarif_pour_client(request.user),
            'date_debut': form['date_debut'].value(),
            'date_fin': form['date_fin'].value(),
        },
    )


@login_required
def mes_reservations(request):
    Reservation.expirer_en_attente()
    photos = Photo.objects.order_by('-principale', 'pk')
    reservations = list(
        request.user.reservations.select_related('appartement').prefetch_related(
            Prefetch(
                'appartement__photos',
                queryset=photos,
                to_attr='photos_reservation',
            )
        )
    )
    return render(
        request,
        'reservations/mes_reservations.html',
        {
            'reservations': reservations,
            'reservations_total': len(reservations),
            'reservations_confirmees': sum(
                reservation.statut == Reservation.CONFIRMEE
                for reservation in reservations
            ),
            'reservations_en_attente': sum(
                reservation.statut == Reservation.EN_ATTENTE
                for reservation in reservations
            ),
        },
    )


@login_required
def detail(request, pk):
    queryset = Reservation.objects.select_related('appartement', 'client')
    if not request.user.est_administrateur():
        queryset = queryset.filter(client=request.user)
    reservation = get_object_or_404(queryset, pk=pk)
    reservation.expirer_si_necessaire()
    return render(request, 'reservations/detail.html', {'reservation': reservation, 'recap': reservation.generer_recap()})


@login_required
@require_http_methods(['GET', 'POST'])
def politiques(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('appartement', 'client'),
        pk=pk,
        client=request.user,
    )
    if reservation.expirer_si_necessaire():
        messages.error(
            request,
            "Le délai de paiement de 24 heures est expiré. L'appartement est de nouveau disponible.",
        )
        return redirect('reservations:detail', pk=reservation.pk)
    if reservation.statut != Reservation.EN_ATTENTE:
        messages.info(request, "Cette réservation ne peut plus être payée.")
        return redirect('reservations:detail', pk=reservation.pk)
    if reservation.politiques_acceptees_le:
        return redirect('payments:payer', reservation_id=reservation.pk)

    if request.method == 'POST':
        try:
            reservation.accepter_politiques()
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return redirect('reservations:detail', pk=reservation.pk)
        messages.success(request, "Politiques acceptées. Vous pouvez maintenant payer par carte bancaire.")
        return redirect('payments:payer', reservation_id=reservation.pk)

    return render(request, 'reservations/politiques.html', {'reservation': reservation})


@login_required
@require_POST
def annuler(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk, client=request.user)
    try:
        reservation.annuler()
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect('reservations:detail', pk=pk)
    messages.success(request, "La réservation a été annulée.")
    return redirect('reservations:detail', pk=pk)


@administrateur_required
def admin_liste(request):
    Reservation.expirer_en_attente()
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
    reservation = get_object_or_404(Reservation, pk=pk)
    try:
        reservation.annuler()
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect('reservations:admin_liste')
    messages.success(request, "Réservation annulée.")
    return redirect('reservations:admin_liste')


@administrateur_required
@require_POST
def admin_supprimer(request, pk):
    get_object_or_404(Reservation, pk=pk).delete()
    messages.success(request, "Réservation supprimée.")
    return redirect('reservations:admin_liste')
