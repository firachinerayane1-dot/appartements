from django.shortcuts import render


def accueil(request):
    return render(request, 'core/accueil.html')


def politique_confidentialite(request):
    return render(request, 'core/politique_confidentialite.html')
