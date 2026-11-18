from .page_cache import public_page_cache
from django.shortcuts import render


@public_page_cache
def accueil(request):
    return render(request, 'core/accueil.html')


@public_page_cache
def politique_confidentialite(request):
    return render(request, 'core/politique_confidentialite.html')
