from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from django.conf import settings
from django.db import transaction

from corpus.models import ChunkDocument, DocumentJuridique


ARTICLE_PATTERN = re.compile(
    r"(?im)^\s*(Article\s+\d+[A-Za-z0-9\-]*)\s*[:.]?"
)


@dataclass(frozen=True)
class TextChunk:
    """Representation temporaire d'un fragment avant sauvegarde."""

    content: str
    numero_article: str | None
    chunk_index: int


def extract_text_from_pdf(file: str | Path | BinaryIO) -> str:
    """Extrait le texte d'un PDF avec pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "La dependance pypdf est requise. Installez: pip install pypdf"
        ) from exc

    reader = PdfReader(file)
    pages_text: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages_text.append(text.strip())

    extracted_text = "\n\n".join(pages_text).strip()
    if not extracted_text:
        raise ValueError("Aucun texte exploitable n'a ete extrait du PDF.")

    return extracted_text


def _split_by_articles(text: str) -> list[tuple[str | None, str]]:
    matches = list(ARTICLE_PATTERN.finditer(text))
    if not matches:
        return [(None, text)]

    sections: list[tuple[str | None, str]] = []
    before_first = text[: matches[0].start()].strip()
    if before_first:
        sections.append((None, before_first))

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        article_title = match.group(1).strip()
        sections.append((article_title, text[start:end].strip()))

    return sections


def _split_long_section(section: str, taille_max: int, overlap: int) -> list[str]:
    words = section.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = min(start + taille_max, len(words))
        chunks.append(" ".join(words[start:end]).strip())
        if end == len(words):
            break
        start = max(end - overlap, start + 1)

    return chunks


def chunk_text(texte: str, taille_max: int = 500, overlap: int = 50) -> list[TextChunk]:
    """
    Decoupe le texte en chunks, en conservant les limites d'articles si possible.

    taille_max et overlap sont exprimes en nombre approximatif de mots.
    """
    if taille_max <= 0:
        raise ValueError("taille_max doit etre superieur a 0.")
    if overlap < 0:
        raise ValueError("overlap ne peut pas etre negatif.")
    if overlap >= taille_max:
        raise ValueError("overlap doit etre inferieur a taille_max.")

    normalized_text = re.sub(r"\s+", " ", texte).strip()
    if not normalized_text:
        return []

    chunks: list[TextChunk] = []
    chunk_index = 0

    for numero_article, section in _split_by_articles(normalized_text):
        for content in _split_long_section(section, taille_max, overlap):
            chunks.append(
                TextChunk(
                    content=content,
                    numero_article=numero_article,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    return chunks


def _get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "La dependance sentence-transformers est requise. "
            "Installez: pip install sentence-transformers"
        ) from exc

    return SentenceTransformer(settings.EMBEDDING_MODEL_NAME)


def _get_chroma_collection():
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "La dependance chromadb est requise. Installez: pip install chromadb"
        ) from exc

    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
    return client.get_or_create_collection(name="code_travail_rdc")


@transaction.atomic
def index_chunks(document: DocumentJuridique) -> int:
    """
    Extrait, decoupe, vectorise et indexe un document juridique.

    L'indexation reste synchrone pour le PFE. Dans une version production,
    cette tache pourrait etre deleguee a Celery.
    """
    with document.fichier.open("rb") as pdf_file:
        text = extract_text_from_pdf(pdf_file)

    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("Le document ne contient aucun chunk indexable.")

    model = _get_embedding_model()
    collection = _get_chroma_collection()

    old_vector_ids = list(document.chunks.values_list("vector_id", flat=True))
    if old_vector_ids:
        collection.delete(ids=old_vector_ids)

    document.chunks.all().delete()

    contents = [chunk.content for chunk in chunks]
    embeddings = model.encode(contents, normalize_embeddings=True).tolist()

    ids: list[str] = []
    metadatas: list[dict[str, str | int | None]] = []
    chunk_objects: list[ChunkDocument] = []

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        vector_id = f"doc-{document.pk}-chunk-{chunk.chunk_index}-{uuid.uuid4().hex}"
        metadata = {
            "document_id": document.pk,
            "document_titre": document.titre,
            "numero_article": chunk.numero_article or "",
            "chunk_index": chunk.chunk_index,
        }

        ids.append(vector_id)
        metadatas.append(metadata)
        chunk_objects.append(
            ChunkDocument(
                document=document,
                contenu_texte=chunk.content,
                numero_article=chunk.numero_article,
                chunk_index=chunk.chunk_index,
                vector_id=vector_id,
            )
        )

    collection.add(
        ids=ids,
        documents=contents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    ChunkDocument.objects.bulk_create(chunk_objects)

    document.statut = DocumentJuridique.Statut.ACTIF
    document.save(update_fields=["statut"])

    return len(chunk_objects)
