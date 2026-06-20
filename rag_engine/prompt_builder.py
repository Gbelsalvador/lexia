from __future__ import annotations

from rag_engine.vector_store import RetrievedChunk


SYSTEM_INSTRUCTION = (
    "Tu es un assistant juridique pédagogique pour les PME de Kinshasa. "
    "Tu expliques le Code du Travail congolais en français simple. "
    "Tu dois utiliser uniquement les extraits fournis et citer les sources. "
    "Si les extraits ne suffisent pas, dis clairement que le corpus fourni "
    "ne permet pas de répondre avec certitude."
)


def build_rag_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    """Construit le prompt augmenté envoyé au modèle de génération."""
    context_parts: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        article = chunk.metadata.get("numero_article", "article non précisé")
        source = chunk.metadata.get("source", "source non précisée")
        context_parts.append(
            f"[Source {index} | {article} | {source}]\n{chunk.content}"
        )

    context = "\n\n".join(context_parts) or "Aucun extrait pertinent trouvé."

    return (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"Contexte juridique récupéré :\n{context}\n\n"
        f"Question de l'utilisateur :\n{question}\n\n"
        "Réponse attendue : réponse vulgarisée, prudente, avec références."
    )
