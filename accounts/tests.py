from django.test import TestCase
from django.urls import reverse

from accounts.models import Utilisateur


class AccountsTests(TestCase):
    """Tests de base inscription et connexion PME."""

    def test_inscription_pme_cree_un_compte_et_connecte(self) -> None:
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "pme_test",
                "email": "pme@example.com",
                "nom_entreprise": "PME Test",
                "secteur_activite": "Services",
                "telephone": "+243000000",
                "password1": "MotDePasseComplexe123!",
                "password2": "MotDePasseComplexe123!",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user = Utilisateur.objects.get(username="pme_test")
        self.assertEqual(user.role, Utilisateur.Role.PME)
        self.assertEqual(user.email, "pme@example.com")

    def test_connexion_accepte_email_ou_username(self) -> None:
        Utilisateur.objects.create_user(
            username="pme_login",
            email="login@example.com",
            password="MotDePasseComplexe123!",
            role=Utilisateur.Role.PME,
        )

        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "login@example.com",
                "password": "MotDePasseComplexe123!",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))

    def test_connexion_ignore_next_externe(self) -> None:
        Utilisateur.objects.create_user(
            username="pme_redirect",
            email="redirect@example.com",
            password="MotDePasseComplexe123!",
            role=Utilisateur.Role.PME,
        )

        response = self.client.post(
            reverse("accounts:login") + "?next=https://evil.example/phishing",
            {
                "username": "pme_redirect",
                "password": "MotDePasseComplexe123!",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))

    def test_deconnexion_exige_post(self) -> None:
        Utilisateur.objects.create_user(
            username="pme_logout",
            password="MotDePasseComplexe123!",
            role=Utilisateur.Role.PME,
        )
        self.client.login(username="pme_logout", password="MotDePasseComplexe123!")

        response = self.client.get(reverse("accounts:logout"))

        self.assertEqual(response.status_code, 405)
