from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.mixins import administrateur_required
from services.reservation_services import chercher_appartements_disponibles
from .forms import AppartementForm, PeriodeVacancesForm, PhotoForm, RechercheDisponibiliteForm
from .models import Appartement, PeriodeVacances, Photo


def liste(request):
    form = RechercheDisponibiliteForm(request.GET or None)
    appartements = Appartement.objects.filter(disponible=True)
    dates_recherche = None
    if form.is_valid() and form.cleaned_data.get('date_debut'):
        debut, fin = form.cleaned_data['date_debut'], form.cleaned_data['date_fin']
        appartements = chercher_appartements_disponibles(debut, fin, request.user)
        dates_recherche = {'date_debut': debut, 'date_fin': fin}
    elif request.GET:
        # Une recherche invalide ne doit jamais présenter le catalogue comme
        # s'il était disponible pour une période qui n'a pas pu être validée.
        appartements = Appartement.objects.none()

    photos_cartes = Photo.objects.order_by('-principale', 'pk')
    appartements = appartements.prefetch_related(
        Prefetch('photos', queryset=photos_cartes, to_attr='photos_carte')
    )
    page = Paginator(appartements, 12).get_page(request.GET.get('page'))
    return render(
        request,
        'apartments/liste.html',
        {'form': form, 'page_obj': page, 'dates_recherche': dates_recherche},
    )


def detail(request, pk):
    appartement = get_object_or_404(Appartement.objects.prefetch_related('photos', 'periodes_vacances'), pk=pk)
    return render(request, 'apartments/detail.html', {'appartement': appartement})


@administrateur_required
def admin_liste(request):
    return render(request, 'apartments/admin_liste.html', {'appartements': Appartement.objects.all()})


@administrateur_required
def appartement_form(request, pk=None):
    appartement = get_object_or_404(Appartement, pk=pk) if pk else None
    form = AppartementForm(request.POST or None, instance=appartement)
    photo_form = PhotoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        appartement = form.save()
        if request.FILES and photo_form.is_valid():
            photo = photo_form.save(commit=False)
            photo.appartement = appartement
            photo.save()
        messages.success(request, "Appartement enregistré.")
        return redirect('apartments:admin_liste')
    return render(request, 'apartments/admin_form.html', {'form': form, 'photo_form': photo_form, 'appartement': appartement})


@administrateur_required
@require_POST
def appartement_supprimer(request, pk):
    try:
        get_object_or_404(Appartement, pk=pk).delete()
    except ProtectedError:
        messages.error(request, "Cet appartement possède des réservations et ne peut pas être supprimé.")
    else:
        messages.success(request, "Appartement supprimé.")
    return redirect('apartments:admin_liste')


@administrateur_required
def vacances_liste(request):
    periodes = PeriodeVacances.objects.select_related('appartement')
    return render(request, 'apartments/vacances_liste.html', {'periodes': periodes})


@administrateur_required
def vacances_form(request, pk=None):
    periode = get_object_or_404(PeriodeVacances, pk=pk) if pk else None
    form = PeriodeVacancesForm(request.POST or None, instance=periode, initial={'appartement': request.GET.get('appartement')})
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Période de vacances enregistrée.")
        return redirect('apartments:vacances_liste')
    return render(request, 'apartments/vacances_form.html', {'form': form, 'periode': periode})


@administrateur_required
@require_POST
def vacances_supprimer(request, pk):
    get_object_or_404(PeriodeVacances, pk=pk).delete()
    messages.success(request, "Période supprimée.")
    return redirect('apartments:vacances_liste')
