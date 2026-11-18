"""Only cookie-free, anonymous public GET requests can share HTML."""
from functools import wraps
from hashlib import sha256
from django.core.cache import cache
from django.utils.cache import patch_cache_control, patch_vary_headers


def public_page_cache(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        eligible = (request.method == 'GET' and not request.COOKIES
                    and not request.user.is_authenticated
                    and not request.headers.get('Authorization'))
        if not eligible:
            response = view(request, *args, **kwargs)
        else:
            digest = sha256(request.build_absolute_uri().encode()).hexdigest()
            key = 'public-page:' + digest
            response = cache.get(key)
            if response is None:
                response = view(request, *args, **kwargs)
                if (response.status_code == 200 and not response.cookies
                        and not request.META.get('CSRF_COOKIE_NEEDS_UPDATE')
                        and not request.session.modified):
                    cache.set(key, response, 60)
        # Redis handles caching; browsers/proxies must revalidate session changes.
        patch_vary_headers(response, ['Cookie', 'Authorization'])
        patch_cache_control(response, private=True, no_store=True)
        return response
    return wrapped
