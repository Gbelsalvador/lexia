from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from chatbot.models import Conversation, Message
from chatbot.rate_limit import is_chat_rate_limited
from rag_engine.pipeline import answer_question

from corpus.services import extract_text_from_pdf
from rag_engine.contract_analysis import analyze_contract

logger = logging.getLogger(__name__)


LLM_FALLBACK_RESPONSE = (
    "Le service de generation est temporairement indisponible. "
    "Votre question a bien ete enregistree, mais l'assistant ne peut pas "
    "produire une reponse fiable pour le moment. Veuillez reessayer plus tard."
)


def _parse_json_body(request: HttpRequest) -> dict[str, Any]:
    """Extrait le corps JSON d'une requete, ou un dict vide en fallback."""
    if not request.body:
        return {}

    try:
        payload = json.loads(request.body.decode("utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _conversation_history(conversation: Conversation) -> list[dict[str, str]]:
    """Retourne un historique court (3-4 echanges) pour le pipeline RAG."""
    recent_messages = conversation.messages.order_by("date_creation", "id")[:]
    payload = [
        {"role": message.role, "content": message.contenu}
        for message in recent_messages
        if message.role in {Message.Role.USER, Message.Role.ASSISTANT}
    ]
    return payload[-8:]


@require_GET
@login_required
def chat_view(request: HttpRequest) -> HttpResponse:
    """Affiche l'interface principale de chat + historique utilisateur."""
    conversations = Conversation.objects.filter(utilisateur=request.user).order_by(
        "-date_mise_a_jour"
    )

    active_conversation: Conversation | None = None
    conversation_id = request.GET.get("conversation")
    nouvelle_conversation = request.GET.get("nouveau") == "1"

    if conversation_id:
        active_conversation = get_object_or_404(
            Conversation,
            pk=conversation_id,
            utilisateur=request.user,
        )
    elif not nouvelle_conversation and conversations.exists():
        active_conversation = conversations.first()

    chat_messages = []
    if active_conversation is not None:
        chat_messages = list(active_conversation.messages.order_by("date_creation", "id"))

    context = {
        "conversations": conversations,
        "active_conversation": active_conversation,
        "chat_messages": chat_messages,
        "nouvelle_conversation": nouvelle_conversation,
    }
    return render(request, "chatbot/chat.html", context)


@require_POST
@login_required
def envoyer_message(request: HttpRequest) -> JsonResponse:
    """
    Endpoint AJAX interne pour envoyer une question au pipeline RAG.

    Retour JSON: {reponse, sources, message_id, conversation_id}
    """
    payload = _parse_json_body(request)
    question = str(payload.get("question") or "").strip()

    if not question:
        return JsonResponse(
            {"erreur": "Veuillez saisir une question."},
            status=400,
        )
    if len(question) > settings.MAX_CHAT_QUESTION_LENGTH:
        return JsonResponse(
            {
                "erreur": (
                    "Votre question est trop longue. "
                    f"Limite: {settings.MAX_CHAT_QUESTION_LENGTH} caracteres."
                )
            },
            status=400,
        )

    if is_chat_rate_limited(request.user.pk):
        logger.warning("Rate limit chat atteint pour user=%s", request.user.pk)
        return JsonResponse(
            {
                "erreur": (
                    "Vous avez atteint la limite de questions pour le moment. "
                    "Veuillez reessayer plus tard."
                )
            },
            status=429,
        )

    conversation_id = payload.get("conversation_id")

    if conversation_id:
        conversation = get_object_or_404(
            Conversation,
            pk=conversation_id,
            utilisateur=request.user,
        )
    else:
        conversation = Conversation.objects.create(
            utilisateur=request.user,
            titre=question[:80],
        )

    Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        contenu=question,
    )

    try:
        result = answer_question(
            question=question,
            conversation=_conversation_history(conversation),
        )
    except Exception:
        logger.exception(
            "Erreur pipeline RAG pour user=%s conversation=%s",
            request.user.pk,
            conversation.pk,
        )
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            contenu=LLM_FALLBACK_RESPONSE,
            sources=[],
        )
        return JsonResponse(
            {
                "reponse": LLM_FALLBACK_RESPONSE,
                "sources": [],
                "message_id": assistant_message.pk,
                "conversation_id": conversation.pk,
                "avertissement": "llm_indisponible",
            }
        )

    reponse = str(result.get("reponse") or "").strip()
    sources = result.get("sources") or []

    assistant_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        contenu=reponse,
        sources=sources,
    )

    if not conversation.titre:
        conversation.titre = question[:80]
    conversation.save(update_fields=["titre", "date_mise_a_jour"])

    return JsonResponse(
        {
            "reponse": reponse,
            "sources": sources,
            "message_id": assistant_message.pk,
            "conversation_id": conversation.pk,
        }
    )


@require_POST
@login_required
def enregistrer_feedback(request: HttpRequest) -> JsonResponse:
    """Enregistre un feedback positif/negatif sur un message assistant."""
    payload = _parse_json_body(request)

    message_id = payload.get("message_id")
    feedback = str(payload.get("feedback") or "").upper().strip()

    if feedback not in {Message.Feedback.POSITIF, Message.Feedback.NEGATIF}:
        return JsonResponse(
            {"erreur": "Feedback invalide. Utilisez POSITIF ou NEGATIF."},
            status=400,
        )

    message = get_object_or_404(
        Message,
        pk=message_id,
        role=Message.Role.ASSISTANT,
        conversation__utilisateur=request.user,
    )

    message.feedback = feedback
    message.save(update_fields=["feedback"])

    return JsonResponse(
        {"ok": True, "message_id": message.pk, "feedback": message.feedback}
    )

 
@require_POST
@login_required
def analyser_contrat(request: HttpRequest) -> JsonResponse:
    """
    Endpoint d'analyse avancee d'un contrat, point par point (RAG + resume + synthese).
 
    Accepte soit un fichier PDF/texte (multipart, champ "fichier"),
    soit du texte colle directement (champ "texte").
    """
    conversation_id = request.POST.get("conversation_id") or None
    question = (request.POST.get("question") or "").strip()
 
    uploaded_file = request.FILES.get("fichier")
    texte_colle = (request.POST.get("texte") or "").strip()
 
    if not uploaded_file and not texte_colle:
        return JsonResponse(
            {"erreur": "Veuillez fournir un fichier de contrat ou coller le texte."},
            status=400,
        )
 
    try:
        if uploaded_file:
            if uploaded_file.name.lower().endswith(".pdf"):
                texte_contrat = extract_text_from_pdf(uploaded_file)
            else:
                texte_contrat = uploaded_file.read().decode("utf-8", errors="ignore")
        else:
            texte_contrat = texte_colle
    except Exception:
        logger.exception("Echec d'extraction du texte du contrat pour user=%s", request.user.pk)
        return JsonResponse(
            {"erreur": "Impossible de lire le contenu du contrat fourni."},
            status=400,
        )
 
    if is_chat_rate_limited(request.user.pk):
        return JsonResponse(
            {"erreur": "Vous avez atteint la limite de requetes pour le moment."},
            status=429,
        )
 
    if conversation_id:
        conversation = get_object_or_404(
            Conversation, pk=conversation_id, utilisateur=request.user,
        )
    else:
        conversation = Conversation.objects.create(
            utilisateur=request.user,
            titre="Analyse de contrat",
        )
 
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        contenu=question or "Analyse de contrat demandee.",
    )
 
    try:
        result = analyze_contract(texte_contrat, question_utilisateur=question or None)
    except ValueError as exc:
        return JsonResponse({"erreur": str(exc)}, status=400)
    except Exception:
        logger.exception("Echec du pipeline d'analyse de contrat pour user=%s", request.user.pk)
        fallback = "L'analyse du contrat a echoue. Veuillez reessayer plus tard."
        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            contenu=fallback,
            sources=[],
        )
        return JsonResponse(
            {
                "reponse": fallback,
                "sources": [],
                "message_id": assistant_message.pk,
                "conversation_id": conversation.pk,
                "avertissement": "analyse_echouee",
            }
        )
 
    assistant_message = Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        contenu=result["reponse"],
        sources=result["sources"],
    )
 
    if not conversation.titre or conversation.titre == "Nouvelle conversation":
        conversation.titre = "Analyse de contrat"
    conversation.save(update_fields=["titre", "date_mise_a_jour"])
 
    return JsonResponse(
        {
            "reponse": result["reponse"],
            "sources": result["sources"],
            "points": result["points"],
            "message_id": assistant_message.pk,
            "conversation_id": conversation.pk,
        }
    )
 