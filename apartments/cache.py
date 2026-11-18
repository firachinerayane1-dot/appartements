from uuid import uuid4
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from .models import Appartement


def catalogue_version():
    key = 'catalogue-version'
    version = cache.get(key)
    if version is None:
        version = uuid4().hex
        cache.set(key, version, None)
    return version


def appartement_detail(pk):
    key = f'catalogue:{catalogue_version()}:{pk}'
    appartement = cache.get(key)
    if appartement is None:
        appartement = get_object_or_404(
            Appartement.objects.prefetch_related('photos', 'periodes_vacances'), pk=pk)
        cache.set(key, appartement, 300)
    return appartement


def invalider_catalogue(**kwargs):
    from django.db import transaction
    transaction.on_commit(lambda: cache.set('catalogue-version', uuid4().hex, None))
