from __future__ import annotations

from rag_engine.vector_store import RetrievedChunk, VectorStore


class Retriever:
    """Récupère les passages juridiques pertinents pour une question."""

    def __init__(self, vector_store: VectorStore, top_k: int = 5) -> None:
        self.vector_store = vector_store
        self.top_k = top_k

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        """Retourne les chunks les plus utiles pour répondre à la question."""
        return self.vector_store.similarity_search(question, top_k=self.top_k)
