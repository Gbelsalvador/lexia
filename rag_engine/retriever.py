from __future__ import annotations

from django.conf import settings

from rag_engine.embeddings import EmbeddingService
from rag_engine.vector_store import ChromaVectorStore, RetrievedChunk


def retrieve_relevant_chunks(
    question: str,
    top_k: int = 5,
    min_score: float | None = None,
) -> list[RetrievedChunk]:
    """
    Recupere les chunks juridiques les plus pertinents pour une question.

    Etapes:
    1) Embedding de la question
    2) Recherche dans ChromaDB
    3) Filtrage par score de pertinence minimal
    4) Retour des chunks avec metadonnees (article, document source)
    """
    cleaned_question = (question or "").strip()
    if not cleaned_question:
        raise ValueError("La question ne peut pas etre vide.")

    threshold = (
        settings.RAG_MIN_RELEVANCE_SCORE
        if min_score is None
        else min_score
    )

    embedding_service = EmbeddingService()
    vector_store = ChromaVectorStore()

    query_embedding = embedding_service.embed(cleaned_question)
    results = vector_store.search(query_embedding=query_embedding, top_k=top_k)

    return [
        chunk
        for chunk in results
        if chunk.score is None or chunk.score >= threshold
    ]
