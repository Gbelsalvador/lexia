from __future__ import annotations

from typing import Any

from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse


def is_admin(user: Any) -> bool:
    """Verifie qu'un utilisateur authentifie a les droits administrateur."""
    return bool(user.is_authenticated and getattr(user, "is_admin", False))


def admin_required(view_func):
    """Restreint une vue aux utilisateurs administrateurs du projet."""

    def wrapped_view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if not is_admin(request.user):
            raise PermissionDenied("Acces reserve aux administrateurs.")

        return view_func(request, *args, **kwargs)

    return wrapped_view


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin pour proteger les vues class-based du dashboard."""

    raise_exception = True

    def test_func(self) -> bool:
        return is_admin(self.request.user)
