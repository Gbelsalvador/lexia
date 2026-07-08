from __future__ import annotations

from django.conf import settings
from django.core.cache import cache


def is_chat_rate_limited(user_id: int) -> bool:
    """
    Verifie si un utilisateur a depasse la limite de questions chat.

    Utilise le cache Django avec une fenetre glissante fixe definie
    par CHAT_RATE_LIMIT_WINDOW_SECONDS.
    """
    cache_key = f"chat_rate:{user_id}"
    count = cache.get(cache_key)

    if count is None:
        cache.set(cache_key, 1, timeout=settings.CHAT_RATE_LIMIT_WINDOW_SECONDS)
        return False

    if count >= settings.CHAT_RATE_LIMIT_COUNT:
        return True

    cache.incr(cache_key)
    return False
