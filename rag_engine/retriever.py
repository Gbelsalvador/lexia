from __future__ import annotations

from rag_engine.embeddings import EmbeddingService
from rag_engine.vector_store import ChromaVectorStore, RetrievedChunk


def retrieve_relevant_chunks(question: str, top_k: int = 5) -> list[RetrievedChunk]:
    """
    Recupere les chunks juridiques les plus pertinents pour une question.

    Etapes:
    1) Embedding de la question
    2) Recherche dans ChromaDB
    3) Retour des chunks avec metadonnees (article, document source)
    """
    cleaned_question = (question or "").strip()
    if not cleaned_question:
        raise ValueError("La question ne peut pas etre vide.")

    embedding_service = EmbeddingService()
    vector_store = ChromaVectorStore()

    query_embedding = embedding_service.embed(cleaned_question)
    return vector_store.search(query_embedding=query_embedding, top_k=top_k)
