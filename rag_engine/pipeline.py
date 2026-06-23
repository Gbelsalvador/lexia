from __future__ import annotations

from typing import Any

from rag_engine.llm_client import LLMClient
from rag_engine.prompt_builder import build_prompt, sanitize_user_text
from rag_engine.retriever import retrieve_relevant_chunks


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
    prompt = build_prompt(
        question=cleaned_question,
        chunks_contexte=chunks,
        conversation=conversation,
    )

    llm_client = LLMClient()
    reponse = llm_client.generate(prompt)

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
