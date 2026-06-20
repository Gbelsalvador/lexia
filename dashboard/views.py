from django.shortcuts import render

from accounts.decorators import admin_required


@admin_required
def home(request):
    """Page d'accueil provisoire du tableau de bord admin."""
    return render(request, "dashboard/home.html")
