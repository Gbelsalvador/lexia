from __future__ import annotations

import logging
from typing import Any

from rag_engine.llm_client import LLMClient
from rag_engine.prompt_builder import build_prompt, sanitize_user_text
from rag_engine.retriever import retrieve_relevant_chunks

logger = logging.getLogger(__name__)


def _fallback_response(question: str, chunks: list[dict[str, Any]]) -> str:
    """Produit une réponse utile et transparente sans LLM externe."""
    if not chunks:
        return (
            "Je n’ai pas trouvé de contexte juridique suffisant dans le corpus pour répondre "
            "de manière fiable. Veuillez reformuler votre question ou vérifier les documents "
            "indexés."
        )

    first_chunk = chunks[0]
    article = first_chunk.get("numero_article") or "Article non précisé"
    document = first_chunk.get("document") or "Document non précisé"
    excerpt = (first_chunk.get("extrait") or "").strip()
    excerpt_text = excerpt[:700].strip()

    return (
        f"Je n’ai pas pu obtenir une réponse générée par le service LLM aujourd’hui. "
        f"Je peux toutefois vous proposer un aperçu basé sur le contexte récupéré : "
        f"le document {document} mentionne {article}. "
        f"Passage pertinent : {excerpt_text or 'aucun extrait disponible.'}"
    )


def answer_question(
    question: str,
    conversation: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Pipeline RAG principal: retrieve -> prompt -> generation -> reponse + sources.

    Args:
        question: Question utilisateur.
        conversation: Historique court de conversation.

    Returns:
        Dictionnaire de la forme:
        {
            "reponse": "...",
            "sources": [
                {
                    "document": "...",
                    "numero_article": "...",
                    "extrait": "..."
                }
            ]
        }
    """
    cleaned_question = (question or "").strip()
    if not cleaned_question:
        raise ValueError("La question ne peut pas etre vide.")
    sanitize_user_text(cleaned_question)

    chunks = retrieve_relevant_chunks(cleaned_question, top_k=5)
    if not chunks:
        logger.warning(
            "Aucun chunk pertinent recupere pour la question (seuil RAG applique)."
        )

    prompt = build_prompt(
        question=cleaned_question,
        chunks_contexte=chunks,
        conversation=conversation,
    )

    llm_client = LLMClient()
    try:
        reponse = llm_client.generate(prompt)
    except Exception:
        logger.exception("Echec generation LLM, activation du fallback local.")
        reponse = _fallback_response(cleaned_question, [
            {
                "document": str(chunk.metadata.get("document_titre") or chunk.metadata.get("source") or ""),
                "numero_article": str(chunk.metadata.get("numero_article") or ""),
                "extrait": (chunk.content or "").strip(),
            }
            for chunk in chunks
        ])

    sources: list[dict[str, str]] = []
    for chunk in chunks:
        document = (
            str(chunk.metadata.get("document_titre") or chunk.metadata.get("source") or "")
            or "Document non precise"
        )
        numero_article = str(chunk.metadata.get("numero_article") or "") or "Article non precise"
        extrait = (chunk.content or "").strip()
        sources.append(
            {
                "document": document,
                "numero_article": numero_article,
                "extrait": extrait,
            }
        )

    return {
        "reponse": reponse,
        "sources": sources,
    }
