from unittest.mock import patch
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.http import HttpResponse
from core.page_cache import public_page_cache
from core.cache_backend import ResilientRedisCache
from redis.exceptions import ConnectionError


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class CacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def request(self, cookie=False):
        request = RequestFactory().get('/', HTTP_COOKIE='sessionid=test' if cookie else '')
        request.user = AnonymousUser()
        SessionMiddleware(lambda r: None).process_request(request)
        return request

    def test_public_cache_and_cookie_isolation(self):
        calls = []
        @public_page_cache
        def view(request):
            calls.append(1)
            return HttpResponse(str(len(calls)))
        self.assertEqual(view(self.request()).content, b'1')
        self.assertEqual(view(self.request()).content, b'1')
        self.assertEqual(view(self.request(True)).content, b'2')
        self.assertEqual(view(self.request()).content, b'1')

    def test_home_fragments_render(self):
        self.assertContains(self.client.get('/'), 'FOSEH')
        self.assertContains(self.client.get('/politique-de-confidentialite/'), 'FOSEH')

    def test_redis_failure_is_cache_miss(self):
        backend = ResilientRedisCache('redis://localhost', {})
        with patch('django.core.cache.backends.redis.RedisCache.get', side_effect=ConnectionError):
            self.assertEqual(backend.get('key', 'fallback'), 'fallback')

    def test_catalogue_invalidated_after_commit(self):
        from apartments.models import Appartement
        from apartments.cache import appartement_detail
        obj = Appartement.objects.create(titre='Avant', description='Test')
        self.assertEqual(appartement_detail(obj.pk).titre, 'Avant')
        with self.captureOnCommitCallbacks(execute=True):
            obj.titre = 'Après'
            obj.save()
        self.assertEqual(appartement_detail(obj.pk).titre, 'Après')
