from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import ConnexionForm, InscriptionForm, ProfilForm


MATRICULE_DEJA_UTILISE = "Ce numéro d'adhérent est déjà utilisé."


def _est_violation_unicite_matricule(exc):
    cause = exc.__cause__
    diagnostic = getattr(cause, 'diag', None)
    contrainte = getattr(diagnostic, 'constraint_name', '') or ''
    return 'matricule' in contrainte.lower() or 'matricule' in str(exc).lower()


def inscription(request):
    if request.user.is_authenticated:
        return redirect('core:accueil')
    form = InscriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                utilisateur = form.save()
        except IntegrityError as exc:
            if not _est_violation_unicite_matricule(exc):
                raise
            form.add_error('matricule', MATRICULE_DEJA_UTILISE)
        else:
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
        etait_client_fm6 = request.user.est_client_fm6()
        try:
            with transaction.atomic():
                utilisateur = form.save()
        except IntegrityError as exc:
            if not _est_violation_unicite_matricule(exc):
                raise
            form.add_error('matricule', MATRICULE_DEJA_UTILISE)
        else:
            if not etait_client_fm6 and utilisateur.est_client_fm6():
                messages.success(
                    request,
                    "Votre profil a été mis à jour et votre type de client est maintenant Client FM6.",
                )
            else:
                messages.success(request, "Votre profil a été mis à jour.")
            return redirect('accounts:profil')
    return render(request, 'accounts/modifier_profil.html', {'form': form})
