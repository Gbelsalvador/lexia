from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings


@dataclass(frozen=True)
class RetrievedChunk:
    """Chunk recupere depuis la base vectorielle."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None


class ChromaVectorStore:
    """
    Wrapper autour de ChromaDB PersistentClient.

    Cette classe centralise l'ajout de chunks et la recherche de similarite
    dans la collection `code_travail_rdc`.
    """

    def __init__(self, collection_name: str = "code_travail_rdc") -> None:
        self.collection_name = collection_name
        self.collection = self._get_collection()

    def _get_collection(self):
        """Recupere ou cree la collection Chroma cible."""
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError(
                "Le package chromadb est requis pour le stockage vectoriel."
            ) from exc

        try:
            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
            return client.get_or_create_collection(name=self.collection_name)
        except Exception as exc:  # pragma: no cover - depend du runtime local
            raise RuntimeError("Impossible d'initialiser la collection ChromaDB.") from exc

    def add_chunks(
        self,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        """
        Ajoute des chunks et leurs embeddings dans ChromaDB.

        Args:
            chunks: Textes des chunks.
            embeddings: Vecteurs numeriques associes.
            metadatas: Metadonnees (article, source, etc.).
            ids: Identifiants uniques de vecteurs.
        """
        if not (len(chunks) == len(embeddings) == len(metadatas) == len(ids)):
            raise ValueError(
                "chunks, embeddings, metadatas et ids doivent avoir la meme longueur."
            )

        if not chunks:
            return

        try:
            self.collection.add(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )
        except Exception as exc:  # pragma: no cover - depend du runtime local
            raise RuntimeError("Echec de l'ajout des chunks dans ChromaDB.") from exc

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[RetrievedChunk]:
        """
        Recherche les chunks les plus pertinents selon l'embedding de question.

        Args:
            query_embedding: Embedding de la question.
            top_k: Nombre maximal de resultats.

        Returns:
            Liste de chunks tries par similarite.
        """
        if not query_embedding:
            raise ValueError("query_embedding ne peut pas etre vide.")

        if top_k <= 0:
            raise ValueError("top_k doit etre strictement superieur a 0.")

        try:
            result = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:  # pragma: no cover - depend du runtime local
            raise RuntimeError("Echec de la recherche de similarite dans ChromaDB.") from exc

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for content, metadata, distance in zip(documents, metadatas, distances, strict=False):
            # Chroma retourne une distance: plus c'est faible, plus c'est proche.
            score = 1.0 / (1.0 + float(distance)) if distance is not None else None
            chunks.append(
                RetrievedChunk(
                    content=content or "",
                    metadata=metadata or {},
                    score=score,
                )
            )

        return chunks
