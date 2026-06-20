from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    """Configuration du modele utilisateur dans l'administration Django."""

    fieldsets = UserAdmin.fieldsets + (
        (
            "Informations PME",
            {
                "fields": (
                    "nom_entreprise",
                    "secteur_activite",
                    "telephone",
                    "role",
                    "date_inscription",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Informations PME",
            {
                "fields": (
                    "email",
                    "nom_entreprise",
                    "secteur_activite",
                    "telephone",
                    "role",
                )
            },
        ),
    )
    list_display = (
        "username",
        "email",
        "nom_entreprise",
        "role",
        "is_staff",
        "is_active",
    )
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "nom_entreprise", "telephone")
    readonly_fields = ("date_inscription",)
