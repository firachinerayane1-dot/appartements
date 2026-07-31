from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import ConnexionForm, InscriptionForm, ProfilForm


def inscription(request):
    if request.user.is_authenticated:
        return redirect('core:accueil')
    form = InscriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        utilisateur = form.save()
        login(request, utilisateur, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, "Votre compte a été créé.")
        return redirect('core:accueil')
    return render(request, 'accounts/inscription.html', {'form': form})


def connexion(request):
    if request.user.is_authenticated:
        return redirect('core:accueil')
    form = ConnexionForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('core:accueil')
    return render(request, 'accounts/connexion.html', {'form': form})


@login_required
def post_login(request):
    return redirect('core:accueil')


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
        etait_enseignant = request.user.est_enseignant()
        utilisateur = form.save()
        if not etait_enseignant and utilisateur.est_enseignant():
            messages.success(
                request,
                "Votre profil a été mis à jour et votre type de client est maintenant Enseignant.",
            )
        else:
            messages.success(request, "Votre profil a été mis à jour.")
        return redirect('accounts:profil')
    return render(request, 'accounts/modifier_profil.html', {'form': form})
