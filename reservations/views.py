from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods, require_POST

from accounts.mixins import administrateur_required
from apartments.models import Appartement, Photo
from services.reservation_services import creer_reservation
from .forms import AcceptationPolitiquesForm, FiltreReservationAdminForm, ReservationForm
from .models import Reservation
from .policies import policies_context



@login_required
def reserver(request, appartement_id):
    appartement = get_object_or_404(
        Appartement.objects.prefetch_related('photos'),
        pk=appartement_id,
        disponible=True,
    )
    form = ReservationForm(request.POST if request.method == 'POST' else None, initial={'date_debut': request.GET.get('date_debut'), 'date_fin': request.GET.get('date_fin')})
    if request.method == 'POST' and form.is_valid():
        try:
            reservation = creer_reservation(request.user, appartement, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
        else:
            messages.success(request, "Dates bloquées pendant 24 heures. Effectuez le virement et envoyez votre reçu au support pour validation.")
            return redirect('payments:payer', reservation_id=reservation.pk)
    debut_valeur = form['date_debut'].value()
    fin_valeur = form['date_fin'].value()
    debut_affiche = debut_valeur if hasattr(debut_valeur, 'strftime') else parse_date(debut_valeur or '')
    fin_affiche = fin_valeur if hasattr(fin_valeur, 'strftime') else parse_date(fin_valeur or '')
    dates_preselectionnees = bool(debut_affiche and fin_affiche and fin_affiche > debut_affiche)
    montant_estime = None
    if dates_preselectionnees:
        montant_estime = appartement.calculer_prix(
            debut_affiche,
            fin_affiche,
            request.user,
        )

    return render(
        request,
        'reservations/reserver.html',
        {
            'form': form,
            'appartement': appartement,
            'tarif_nuit': appartement.tarif_pour_client(request.user),
            'date_debut': form['date_debut'].value(),
            'date_fin': form['date_fin'].value(),
            'date_debut_affichee': debut_affiche,
            'date_fin_affichee': fin_affiche,
            'dates_preselectionnees': dates_preselectionnees,
            'duree_sejour': (fin_affiche - debut_affiche).days if dates_preselectionnees else None,
            'montant_estime': montant_estime,
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
    queryset = Reservation.objects.select_related('appartement', 'client').prefetch_related(
        'appartement__photos'
    )
    if not request.user.est_administrateur():
        queryset = queryset.filter(client=request.user)
    reservation = get_object_or_404(queryset, pk=pk)
    reservation.expirer_si_necessaire()
    template = 'reservations/admin_detail.html' if request.user.est_administrateur() else 'reservations/detail.html'
    return render(request, template, {'reservation': reservation, 'recap': reservation.generer_recap()})


@require_http_methods(['GET'])
def politiques_generales(request):
    return render(request, 'reservations/politiques.html', policies_context())


@login_required
@require_http_methods(['GET', 'POST'])
def politiques(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk, client=request.user)
    reservation.expirer_si_necessaire()
    form = AcceptationPolitiquesForm(request.POST if request.method == 'POST' else None)
    peut_accepter = reservation.statut == Reservation.EN_ATTENTE and not reservation.politiques_acceptees_le
    if request.method == 'POST' and peut_accepter and form.is_valid():
        try:
            reservation.accepter_politiques()
        except ValidationError as exc:
            form.add_error(None, exc.messages[0])
        else:
            return redirect('payments:payer', reservation_id=reservation.pk)
    return render(request, 'reservations/politiques.html', {
        'reservation': reservation, 'form': form, 'peut_accepter': peut_accepter,
        **policies_context(reservation),
    })


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
        recherche = form.cleaned_data.get('recherche')
        if recherche:
            reservations = reservations.filter(Q(numero_reservation__icontains=recherche) | Q(client__nom__icontains=recherche) | Q(client__prenom__icontains=recherche) | Q(client__email__icontains=recherche))
        if form.cleaned_data.get('statut'):
            reservations = reservations.filter(statut=form.cleaned_data['statut'])
        if form.cleaned_data.get('appartement'):
            reservations = reservations.filter(appartement=form.cleaned_data['appartement'])
        if form.cleaned_data.get('date_debut'):
            reservations = reservations.filter(date_fin__gt=form.cleaned_data['date_debut'])
        if form.cleaned_data.get('date_fin'):
            reservations = reservations.filter(date_debut__lt=form.cleaned_data['date_fin'])
    page = Paginator(reservations, 20).get_page(request.GET.get('page'))
    return render(request, 'reservations/admin_liste.html', {'form': form, 'reservations': page, 'page_obj': page})


@administrateur_required
@require_POST
def admin_annuler(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    try:
        reservation.annuler(motif=request.POST.get('motif', 'CLIENT'), administrateur=request.user)
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
