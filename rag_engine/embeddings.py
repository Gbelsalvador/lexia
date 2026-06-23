from __future__ import annotations

from typing import Iterable, Sequence

from django.conf import settings


class EmbeddingService:
    """
    Service d'embeddings local base sur sentence-transformers.

    Le modele par defaut est `paraphrase-multilingual-MiniLM-L12-v2` pour
    prendre en charge le francais sans cout API.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._model = self._load_model()

    def _load_model(self):
        """Charge le modele sentence-transformers configure."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Le package sentence-transformers est requis pour les embeddings."
            ) from exc

        try:
            return SentenceTransformer(self.model_name)
        except Exception as exc:  # pragma: no cover - depend du runtime local
            raise RuntimeError(
                f"Impossible de charger le modele d'embeddings '{self.model_name}'."
            ) from exc

    def embed(self, texte: str) -> list[float]:
        """
        Genere l'embedding d'un texte unique.

        Args:
            texte: Texte a vectoriser.

        Returns:
            Liste de flottants representant le vecteur d'embedding.
        """
        cleaned_text = (texte or "").strip()
        if not cleaned_text:
            raise ValueError("Le texte a embedder ne peut pas etre vide.")

        try:
            vector: Sequence[float] = self._model.encode(
                cleaned_text,
                normalize_embeddings=True,
            ).tolist()
        except Exception as exc:  # pragma: no cover - depend du runtime local
            raise RuntimeError("Echec de generation de l'embedding du texte.") from exc

        return [float(value) for value in vector]

    def embed_many(self, textes: Iterable[str]) -> list[list[float]]:
        """
        Genere les embeddings pour plusieurs textes.

        Args:
            textes: Collection de textes a vectoriser.

        Returns:
            Liste de vecteurs d'embedding.
        """
        items = [texte.strip() for texte in textes if texte and texte.strip()]
        if not items:
            return []

        try:
            vectors = self._model.encode(
                items,
                normalize_embeddings=True,
            ).tolist()
        except Exception as exc:  # pragma: no cover - depend du runtime local
            raise RuntimeError("Echec de generation des embeddings de documents.") from exc

        return [[float(value) for value in vector] for vector in vectors]
