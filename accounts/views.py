from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from accounts.forms import LoginForm, PMERegistrationForm


@require_http_methods(["GET", "POST"])
def register(request):
    """Inscrit une PME et ouvre directement sa session."""
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    if request.method == "POST":
        form = PMERegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(
                request,
                "Votre compte PME a ete cree avec succes.",
            )
            return redirect("accounts:profile")

        messages.error(request, "Veuillez corriger les erreurs du formulaire.")
    else:
        form = PMERegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Connecte un utilisateur existant."""
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    if request.method == "POST":
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            messages.success(request, "Connexion reussie.")
            next_url = request.GET.get("next")
            return redirect(next_url or "accounts:profile")

        messages.error(request, "Identifiants invalides.")
    else:
        form = LoginForm(request=request)

    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    """Ferme la session active."""
    auth_logout(request)
    messages.info(request, "Vous avez ete deconnecte.")
    return redirect("accounts:login")


@login_required
def profile(request):
    """Affiche le profil de l'utilisateur connecte."""
    return render(request, "accounts/profile.html")
