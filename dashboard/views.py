from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from accounts.decorators import admin_required
from accounts.models import Utilisateur
from chatbot.models import Conversation, Message
from corpus.models import ChunkDocument, DocumentJuridique


def _date_range_labels(days: int = 30) -> list[str]:
    """Retourne les libelles de dates couvrant les derniers jours."""
    today = timezone.localdate()
    first_day = today - timedelta(days=days - 1)
    return [(first_day + timedelta(days=offset)).isoformat() for offset in range(days)]


def _questions_par_jour() -> list[dict[str, Any]]:
    """Agrege les questions utilisateur par jour sur les 30 derniers jours."""
    labels = _date_range_labels(days=30)
    since = timezone.now() - timedelta(days=29)

    rows = (
        Message.objects.filter(
            role=Message.Role.USER,
            date_creation__date__gte=since.date(),
        )
        .annotate(jour=TruncDate("date_creation"))
        .values("jour")
        .annotate(total=Count("id"))
        .order_by("jour")
    )
    totals = {row["jour"].isoformat(): row["total"] for row in rows if row["jour"]}

    return [{"date": label, "total": totals.get(label, 0)} for label in labels]


def _feedback_repartition() -> list[dict[str, Any]]:
    """Agrege les feedbacks assistant positifs et negatifs."""
    rows = (
        Message.objects.filter(
            role=Message.Role.ASSISTANT,
            feedback__in=[Message.Feedback.POSITIF, Message.Feedback.NEGATIF],
        )
        .values("feedback")
        .annotate(total=Count("id"))
        .order_by("feedback")
    )
    totals = {row["feedback"]: row["total"] for row in rows}

    return [
        {"label": "Positifs", "total": totals.get(Message.Feedback.POSITIF, 0)},
        {"label": "Negatifs", "total": totals.get(Message.Feedback.NEGATIF, 0)},
    ]


def _top_articles_cites() -> list[dict[str, Any]]:
    """
    Calcule les articles les plus cites depuis les sources JSON des reponses.

    Les sources sont stockees dans Message.sources, donc cette partie reste en
    Python pour rester compatible SQLite/PostgreSQL sans SQL JSON specifique.
    """
    counter: Counter[str] = Counter()

    messages = Message.objects.filter(
        role=Message.Role.ASSISTANT,
        sources__isnull=False,
    ).only("sources")

    for message in messages:
        for source in message.sources or []:
            numero_article = str(source.get("numero_article") or "").strip()
            if numero_article:
                counter[numero_article] += 1

    return [
        {"article": article, "total": total}
        for article, total in counter.most_common(5)
    ]


@admin_required
def home(request: HttpRequest) -> HttpResponse:
    """Vue d'ensemble du tableau de bord administrateur."""
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)

    total_pme = Utilisateur.objects.filter(role=Utilisateur.Role.PME).count()
    total_questions = Message.objects.filter(role=Message.Role.USER).count()
    questions_7_jours = Message.objects.filter(
        role=Message.Role.USER,
        date_creation__gte=seven_days_ago,
    ).count()

    feedbacks = Message.objects.filter(
        role=Message.Role.ASSISTANT,
        feedback__in=[Message.Feedback.POSITIF, Message.Feedback.NEGATIF],
    )
    total_feedbacks = feedbacks.count()
    feedbacks_positifs = feedbacks.filter(feedback=Message.Feedback.POSITIF).count()
    taux_satisfaction = (
        round((feedbacks_positifs / total_feedbacks) * 100, 1)
        if total_feedbacks
        else 0
    )

    context = {
        "total_pme": total_pme,
        "total_questions": total_questions,
        "questions_7_jours": questions_7_jours,
        "taux_satisfaction": taux_satisfaction,
        "total_feedbacks": total_feedbacks,
        "documents_indexes": DocumentJuridique.objects.filter(
            statut=DocumentJuridique.Statut.ACTIF
        ).count(),
        "chunks_indexes": ChunkDocument.objects.count(),
        "conversations_recentes": Conversation.objects.select_related("utilisateur")
        .annotate(nb_messages=Count("messages"))
        .order_by("-date_mise_a_jour")[:8],
        "questions_par_jour": _questions_par_jour(),
        "feedback_repartition": _feedback_repartition(),
        "top_articles": _top_articles_cites(),
    }
    return render(request, "dashboard/dashboard.html", context)


@admin_required
def utilisateurs_pme(request: HttpRequest) -> HttpResponse:
    """Liste les utilisateurs PME avec recherche et filtre simple."""
    query = (request.GET.get("q") or "").strip()
    secteur = (request.GET.get("secteur") or "").strip()

    utilisateurs = get_user_model().objects.filter(role=Utilisateur.Role.PME)

    if query:
        utilisateurs = utilisateurs.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(nom_entreprise__icontains=query)
            | Q(telephone__icontains=query)
        )

    if secteur:
        utilisateurs = utilisateurs.filter(secteur_activite__icontains=secteur)

    utilisateurs = utilisateurs.annotate(
        nb_conversations=Count("conversations", distinct=True),
        nb_questions=Count(
            "conversations__messages",
            filter=Q(conversations__messages__role=Message.Role.USER),
        ),
    ).order_by("username")

    secteurs = (
        get_user_model()
        .objects.filter(role=Utilisateur.Role.PME)
        .exclude(secteur_activite="")
        .values_list("secteur_activite", flat=True)
        .distinct()
        .order_by("secteur_activite")
    )

    return render(
        request,
        "dashboard/utilisateurs.html",
        {
            "utilisateurs": utilisateurs,
            "secteurs": secteurs,
            "query": query,
            "secteur_selectionne": secteur,
        },
    )


@admin_required
def conversation_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Affiche une conversation complete pour audit et controle qualite."""
    conversation = get_object_or_404(
        Conversation.objects.select_related("utilisateur").prefetch_related("messages"),
        pk=pk,
    )
    messages = conversation.messages.order_by("date_creation", "id")

    return render(
        request,
        "dashboard/conversation_detail.html",
        {"conversation": conversation, "messages": messages},
    )
