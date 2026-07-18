from django.shortcuts import render

from apartments.models import Appartement


def accueil(request):
    appartements = Appartement.objects.filter(disponible=True).prefetch_related('photos')
    return render(request, 'core/accueil.html', {
        'appartements_en_vedette': appartements[:3],
        'nombre_appartements': appartements.count(),
    })
