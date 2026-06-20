from __future__ import annotations

from typing import Iterable


class EmbeddingClient:
    """Interface de base pour transformer du texte en vecteurs."""

    def embed_text(self, text: str) -> list[float]:
        """Retourne le vecteur d'embedding d'un texte."""
        raise NotImplementedError

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        """Retourne les vecteurs d'embeddings d'une liste de textes."""
        return [self.embed_text(text) for text in texts]
