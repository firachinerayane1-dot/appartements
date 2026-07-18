from datetime import timedelta
from io import BytesIO

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.mixins import administrateur_required
from apartments.models import Appartement
from payments.models import Paiement
from reservations.models import Reservation
from .forms import PeriodeForm


def _bornes(form):
    if form.is_valid() and form.cleaned_data.get('date_debut'):
        return form.cleaned_data['date_debut'], form.cleaned_data['date_fin']
    fin = timezone.localdate() + timedelta(days=1)
    return fin - timedelta(days=30), fin


def _reservations_filtrees(debut, fin):
    return Reservation.objects.filter(date_debut__lt=fin, date_fin__gt=debut)


@administrateur_required
def index(request):
    form = PeriodeForm(request.GET or None)
    debut, fin = _bornes(form)
    reservations = _reservations_filtrees(debut, fin)
    nb_appartements = Appartement.objects.filter(disponible=True).count()
    jours_periode = max((fin - debut).days, 1)
    jours_occupes = 0
    for reservation in reservations.filter(statut__in=(Reservation.CONFIRMEE, Reservation.TERMINEE)):
        jours_occupes += (min(reservation.date_fin, fin) - max(reservation.date_debut, debut)).days
    capacite = nb_appartements * jours_periode
    taux_occupation = round((jours_occupes / capacite) * 100, 2) if capacite else 0
    revenu = Paiement.objects.filter(
        statut=Paiement.PAYE, date_paiement__date__gte=debut, date_paiement__date__lt=fin
    ).aggregate(total=Sum('montant'))['total'] or 0
    compteurs = reservations.aggregate(
        total=Count('id'),
        confirmees=Count('id', filter=Q(statut=Reservation.CONFIRMEE)),
        annulees=Count('id', filter=Q(statut=Reservation.ANNULEE)),
    )
    par_mois = list(
        reservations.annotate(mois=TruncMonth('date_debut'))
        .values('mois').annotate(total=Count('id')).order_by('mois')
    )
    contexte = {
        'form': form, 'date_debut': debut, 'date_fin': fin, 'taux_occupation': taux_occupation,
        'revenu_total': revenu, 'compteurs': compteurs, 'reservations_par_mois': par_mois,
    }
    return render(request, 'dashboard/index.html', contexte)


@administrateur_required
def export_excel(request):
    from openpyxl import Workbook

    form = PeriodeForm(request.GET or None)
    debut, fin = _bornes(form)
    reservations = _reservations_filtrees(debut, fin).select_related('client', 'appartement')
    workbook = Workbook()
    feuille = workbook.active
    feuille.title = 'Réservations'
    feuille.append(['Client', 'Appartement', 'Date début', 'Date fin', 'Montant', 'Statut'])
    for reservation in reservations:
        feuille.append([
            str(reservation.client), reservation.appartement.titre, reservation.date_debut,
            reservation.date_fin, float(reservation.montant_total), reservation.get_statut_display(),
        ])
    flux = BytesIO()
    workbook.save(flux)
    response = HttpResponse(flux.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reservations-{debut}-{fin}.xlsx"'
    return response
