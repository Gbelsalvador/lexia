from django.test import TestCase
from django.urls import reverse

from accounts.models import Utilisateur
from chatbot.models import Conversation, Message


class DashboardPermissionTests(TestCase):
    """Tests des permissions admin du dashboard."""

    def setUp(self) -> None:
        self.admin = Utilisateur.objects.create_user(
            username="admin_dashboard",
            password="MotDePasseComplexe123!",
            role=Utilisateur.Role.ADMIN,
        )
        self.pme = Utilisateur.objects.create_user(
            username="pme_dashboard",
            password="MotDePasseComplexe123!",
            role=Utilisateur.Role.PME,
        )

    def test_dashboard_reserve_aux_admins(self) -> None:
        self.client.force_login(self.pme)

        response = self.client.get(reverse("dashboard:home"))

        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_accessible_admin(self) -> None:
        self.client.force_login(self.admin)

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 200)

    def test_detail_conversation_accessible_admin(self) -> None:
        conversation = Conversation.objects.create(
            utilisateur=self.pme,
            titre="Audit",
        )
        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            contenu="Question",
        )
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("dashboard:conversation_detail", args=[conversation.pk])
        )

        self.assertEqual(response.status_code, 200)
