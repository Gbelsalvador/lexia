from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Utilisateur(AbstractUser):
    """Utilisateur du systeme : PME ou administrateur."""

    class Role(models.TextChoices):
        PME = "PME", "PME"
        ADMIN = "ADMIN", "Administrateur"

    nom_entreprise = models.CharField(
        "nom de l'entreprise",
        max_length=255,
        blank=True,
    )
    secteur_activite = models.CharField(
        "secteur d'activite",
        max_length=255,
        blank=True,
    )
    telephone = models.CharField(
        "telephone",
        max_length=30,
        blank=True,
    )
    role = models.CharField(
        "role",
        max_length=20,
        choices=Role.choices,
        default=Role.PME,
    )
    date_inscription = models.DateTimeField(
        "date d'inscription",
        default=timezone.now,
    )

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    @property
    def is_admin(self) -> bool:
        """Indique si l'utilisateur peut acceder au tableau de bord admin."""
        return self.role == self.Role.ADMIN or self.is_staff or self.is_superuser

    def __str__(self) -> str:
        if self.nom_entreprise:
            return f"{self.username} - {self.nom_entreprise}"
        return self.username
