from __future__ import annotations

from typing import Any

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin


def is_admin(user: Any) -> bool:
    """Verifie qu'un utilisateur authentifie a les droits administrateur."""
    return bool(user.is_authenticated and getattr(user, "is_admin", False))


def admin_required(view_func):
    """Restreint une vue aux utilisateurs administrateurs du projet."""
    return user_passes_test(
        is_admin,
        login_url="accounts:login",
        redirect_field_name="next",
    )(view_func)


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin pour proteger les vues class-based du dashboard."""

    raise_exception = True

    def test_func(self) -> bool:
        return is_admin(self.request.user)
