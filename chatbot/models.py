from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    """Conversation entre un utilisateur PME et l'assistant juridique."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
    )
    titre = models.CharField(max_length=255, blank=True)
    date_creation = models.DateTimeField(default=timezone.now)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "conversation"
        verbose_name_plural = "conversations"
        ordering = ["-date_mise_a_jour"]

    def __str__(self) -> str:
        return self.titre or f"Conversation #{self.pk}"


class Message(models.Model):
    """Message unitaire d'une conversation (utilisateur ou assistant)."""

    class Role(models.TextChoices):
        USER = "user", "Utilisateur"
        ASSISTANT = "assistant", "Assistant"

    class Feedback(models.TextChoices):
        POSITIF = "POSITIF", "Positif"
        NEGATIF = "NEGATIF", "Negatif"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    contenu = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    feedback = models.CharField(
        max_length=20,
        choices=Feedback.choices,
        blank=True,
    )
    date_creation = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "message"
        verbose_name_plural = "messages"
        ordering = ["date_creation", "id"]

    def __str__(self) -> str:
        return f"{self.get_role_display()} - conv {self.conversation_id}"
