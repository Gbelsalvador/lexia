from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from accounts.models import Utilisateur


class BootstrapFormMixin:
    """Ajoute automatiquement les classes Bootstrap aux champs."""

    def _apply_bootstrap_classes(self) -> None:
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} form-control".strip()


class PMERegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Formulaire d'inscription pour les utilisateurs PME."""

    email = forms.EmailField(required=True, label="Adresse email")
    nom_entreprise = forms.CharField(
        required=True,
        label="Nom de l'entreprise",
        max_length=255,
    )
    secteur_activite = forms.CharField(
        required=False,
        label="Secteur d'activite",
        max_length=255,
    )
    telephone = forms.CharField(
        required=False,
        label="Telephone",
        max_length=30,
    )

    class Meta:
        model = Utilisateur
        fields = (
            "username",
            "email",
            "nom_entreprise",
            "secteur_activite",
            "telephone",
            "password1",
            "password2",
        )
        labels = {
            "username": "Nom d'utilisateur",
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_classes()

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if Utilisateur.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cette adresse email est deja utilisee.")
        return email

    def save(self, commit: bool = True) -> Utilisateur:
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.nom_entreprise = self.cleaned_data["nom_entreprise"]
        user.secteur_activite = self.cleaned_data["secteur_activite"]
        user.telephone = self.cleaned_data["telephone"]
        user.role = Utilisateur.Role.PME

        if commit:
            user.save()

        return user


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """Formulaire de connexion avec rendu Bootstrap."""

    username = forms.CharField(label="Nom d'utilisateur ou email")
    password = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, request=None, *args, **kwargs) -> None:
        super().__init__(request=request, *args, **kwargs)
        self._apply_bootstrap_classes()

    def clean(self) -> dict:
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            identifier = username.strip()
            if "@" in identifier:
                user = Utilisateur.objects.filter(email__iexact=identifier).first()
                if user:
                    identifier = user.get_username()

            self.user_cache = authenticate(
                self.request,
                username=identifier,
                password=password,
            )

            if self.user_cache is None:
                raise forms.ValidationError(
                    "Identifiants invalides.",
                    code="invalid_login",
                )

            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
