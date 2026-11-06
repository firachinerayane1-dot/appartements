from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def destination_sure(request, destination):
    if destination and url_has_allowed_host_and_scheme(
        destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destination
    return reverse('core:accueil')


def destination_apres_connexion(request):
    return destination_sure(request, request.POST.get('next', request.GET.get('next', '')))
