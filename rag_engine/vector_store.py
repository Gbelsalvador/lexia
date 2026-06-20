from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievedChunk:
    """Chunk récupéré depuis la base vectorielle."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None


class VectorStore:
    """Interface minimale pour un stockage vectoriel compatible ChromaDB."""

    def add_texts(
        self,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Ajoute des textes et leurs métadonnées dans l'index."""
        raise NotImplementedError

    def similarity_search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        """Recherche les chunks les plus proches d'une question."""
        raise NotImplementedError
