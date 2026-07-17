from django.conf import settings


def google_oauth(request):
    return {'google_oauth_configured': settings.GOOGLE_OAUTH_CONFIGURED}
