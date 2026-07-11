from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import InscriptionForm, ConnexionForm
from django.contrib.auth.decorators import login_required


def inscription(request):
    """
    Vue pour creerCompte() — affiche le formulaire ET traite la soumission.
    """
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            utilisateur = form.save()
            login(request, utilisateur)
            return redirect('accueil')
    else:
        form = InscriptionForm()

    return render(request, 'accounts/inscription.html', {'form': form})


def accueil(request):
    return render(request, 'accounts/accueil.html')


def connexion(request):
    """
    Vue pour seConnecter().
    """
    if request.method == 'POST':
        form = ConnexionForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            utilisateur = authenticate(request, username=email, password=password)
            if utilisateur is not None:
                login(request, utilisateur)
                return redirect('accueil')
    else:
        form = ConnexionForm()

    return render(request, 'accounts/connexion.html', {'form': form})


def deconnexion(request):
    """
    Vue pour seDeconnecter().
    """
    logout(request)
    return redirect('connexion')

@login_required(login_url='connexion')
def accueil(request):
    return render(request, 'accounts/accueil.html')

def inscription(request):
    if request.user.is_authenticated:
        return redirect('accueil')
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            utilisateur = form.save()
            login(request, utilisateur)
            return redirect('accueil')
    else:
        form = InscriptionForm()
    return render(request, 'accounts/inscription.html', {'form': form})


def connexion(request):
    if request.user.is_authenticated:
        return redirect('accueil')
    if request.method == 'POST':
        form = ConnexionForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            utilisateur = authenticate(request, username=email, password=password)
            if utilisateur is not None:
                login(request, utilisateur)
                return redirect('accueil')
    else:
        form = ConnexionForm()
    return render(request, 'accounts/connexion.html', {'form': form})