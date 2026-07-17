from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import ConnexionForm, InscriptionForm, ProfilForm


def _dashboard_url(user):
    return 'dashboard:index' if user.est_administrateur() else 'reservations:mes_reservations'


def inscription(request):
    if request.user.is_authenticated:
        return redirect(_dashboard_url(request.user))
    form = InscriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        utilisateur = form.save()
        login(request, utilisateur, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, "Votre compte a été créé.")
        return redirect(_dashboard_url(utilisateur))
    return render(request, 'accounts/inscription.html', {'form': form})


def connexion(request):
    if request.user.is_authenticated:
        return redirect(_dashboard_url(request.user))
    form = ConnexionForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect(_dashboard_url(form.get_user()))
    return render(request, 'accounts/connexion.html', {'form': form})


@login_required
def post_login(request):
    return redirect(_dashboard_url(request.user))


@require_POST
def deconnexion(request):
    logout(request)
    return redirect('accounts:connexion')


@login_required
def profil(request):
    return render(request, 'accounts/profil.html')


@login_required
def modifier_profil(request):
    form = ProfilForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Votre profil a été mis à jour.")
        return redirect('accounts:profil')
    return render(request, 'accounts/modifier_profil.html', {'form': form})
