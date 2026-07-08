import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import Utilisateur
from chatbot.models import Conversation, Message


class ChatbotSecurityTests(TestCase):
    """Tests CSRF, limites de question et fallback API."""

    def setUp(self) -> None:
        self.user = Utilisateur.objects.create_user(
            username="pme_chat",
            password="MotDePasseComplexe123!",
            role=Utilisateur.Role.PME,
        )

    def test_envoyer_message_exige_csrf_quand_active(self) -> None:
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        response = client.post(
            reverse("chatbot:envoyer_message"),
            data=json.dumps({"question": "Bonjour"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    @patch("chatbot.views.answer_question")
    def test_envoyer_message_avec_csrf_sauvegarde_messages(self, mock_answer) -> None:
        mock_answer.return_value = {
            "reponse": "Reponse test",
            "sources": [{"document": "Code", "numero_article": "Article 1", "extrait": "..."}],
        }
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(reverse("chatbot:chat"))
        csrf_token = client.cookies["csrftoken"].value

        response = client.post(
            reverse("chatbot:envoyer_message"),
            data=json.dumps({"question": "Question test"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Message.objects.count(), 2)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(response.json()["reponse"], "Reponse test")

    def test_chat_page_n_affiche_plus_les_objets_message_en_mode_plain(self) -> None:
        conversation = Conversation.objects.create(utilisateur=self.user, titre="Test")
        Message.objects.create(conversation=conversation, role=Message.Role.USER, contenu="Bonjour")

        self.client.force_login(self.user)
        response = self.client.get(reverse("chatbot:chat"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bonjour")
        self.assertNotContains(response, "Utilisateur - conv")
        self.assertNotContains(response, "Assistant - conv")

    @override_settings(MAX_CHAT_QUESTION_LENGTH=10)
    def test_envoyer_message_rejette_question_trop_longue(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("chatbot:envoyer_message"),
            data=json.dumps({"question": "x" * 11}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("chatbot.views.answer_question", side_effect=RuntimeError("LLM down"))
    def test_envoyer_message_retourne_fallback_si_llm_indisponible(self, mock_answer) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("chatbot:envoyer_message"),
            data=json.dumps({"question": "Question test"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["avertissement"], "llm_indisponible")
        self.assertEqual(Message.objects.filter(role=Message.Role.ASSISTANT).count(), 1)

    @override_settings(CHAT_RATE_LIMIT_COUNT=1, CHAT_RATE_LIMIT_WINDOW_SECONDS=3600)
    @patch("chatbot.views.answer_question")
    def test_envoyer_message_applique_rate_limit(self, mock_answer) -> None:
        mock_answer.return_value = {
            "reponse": "Reponse test",
            "sources": [],
        }
        self.client.force_login(self.user)

        first = self.client.post(
            reverse("chatbot:envoyer_message"),
            data=json.dumps({"question": "Question 1"}),
            content_type="application/json",
        )
        second = self.client.post(
            reverse("chatbot:envoyer_message"),
            data=json.dumps({"question": "Question 2"}),
            content_type="application/json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
