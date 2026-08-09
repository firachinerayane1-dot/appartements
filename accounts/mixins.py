from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url


def client_fm6_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), resolve_url(settings.LOGIN_URL))
        if not request.user.est_client_fm6():
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped


# Ancien nom conservé pour les éventuels imports existants.
enseignant_required = client_fm6_required


class AdministrateurRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.est_administrateur()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


def administrateur_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), resolve_url(settings.LOGIN_URL))
        if not request.user.est_administrateur():
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapped
