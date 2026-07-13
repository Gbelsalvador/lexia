from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from rag_engine.llm_client import LLMClient
from rag_engine.prompt_builder import (
    build_clause_summary_prompt,
    build_synthesis_prompt,
    sanitize_user_text,
)
from rag_engine.retriever import retrieve_relevant_chunks
from rag_engine.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)


CLAUSE_MARKER_PATTERN = re.compile(
    r"(?im)^\s*(?:Article\s+\d+[A-Za-z0-9\-]*|Clause\s+\d+|"
    r"\d{1,2}[\.\)]\s+|[IVXLC]{1,6}[\.\)]\s+)"
)

MAX_CLAUSES = 12
MAX_WORDS_PER_CLAUSE = 400
MIN_WORDS_PER_CLAUSE = 15
CLAUSE_MAX_CHARS = 2800  # marge de securite sous la limite de 3000 de sanitize_user_text


@dataclass(frozen=True)
class ClauseResult:
    """Resultat du traitement individuel d'un point (clause) du contrat."""

    index: int
    titre: str
    resume: str
    sources: list[dict[str, str]]


def split_contract_into_clauses(texte_contrat: str) -> list[tuple[str, str]]:
    """
    Divise un contrat en points (clauses) traitables individuellement.

    1) Detecte les marqueurs habituels (Article, Clause, numerotation 1./I.).
    2) A defaut, replie sur un decoupage par paragraphes groupes en blocs
       de taille fixe, pour ne jamais envoyer tout le contrat en un bloc.
    3) Fusionne les fragments trop courts (titres isoles) avec leur voisin.
    4) Plafonne le nombre de points pour borner le nombre d'appels LLM.
    """
    raw_text = (texte_contrat or "").strip()
    if not raw_text:
        return []

    matches = list(CLAUSE_MARKER_PATTERN.finditer(raw_text))
    sections: list[tuple[str, str]] = []

    if matches:
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_text)
            section_text = raw_text[start:end].strip()
            if not section_text:
                continue
            titre = section_text.split("\n", 1)[0].strip()[:80] or f"Point {index + 1}"
            sections.append((titre, section_text))
    else:
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        buffer_words: list[str] = []
        section_index = 1

        for paragraph in paragraphs:
            buffer_words.extend(paragraph.split())
            if len(buffer_words) >= MAX_WORDS_PER_CLAUSE:
                sections.append((f"Point {section_index}", " ".join(buffer_words)))
                section_index += 1
                buffer_words = []

        if buffer_words:
            sections.append((f"Point {section_index}", " ".join(buffer_words)))

    merged: list[tuple[str, str]] = []
    pending_title: str | None = None
    pending_content = ""

    for titre, contenu in sections:
        if pending_content:
            contenu = f"{pending_content}\n{contenu}"
            titre = pending_title or titre
            pending_content = ""
            pending_title = None

        if len(contenu.split()) < MIN_WORDS_PER_CLAUSE:
            pending_title = titre
            pending_content = contenu
            continue

        merged.append((titre, contenu))

    if pending_content:
        if merged:
            last_titre, last_contenu = merged[-1]
            merged[-1] = (last_titre, f"{last_contenu}\n{pending_content}")
        else:
            merged.append((pending_title or "Point 1", pending_content))

    if len(merged) > MAX_CLAUSES:
        head = merged[: MAX_CLAUSES - 1]
        tail_titre, tail_contenu = merged[MAX_CLAUSES - 1]
        for titre, contenu in merged[MAX_CLAUSES:]:
            tail_contenu = f"{tail_contenu}\n\n{contenu}"
        # Bug corrige : sans cette troncature, un contrat avec plus de
        # MAX_CLAUSES points produisait un dernier bloc de taille illimitee
        # (toutes les clauses excedentaires concatenees), ce qui depassait
        # systematiquement la limite de 3000 caracteres appliquee plus loin
        # dans analyze_clause et faisait echouer toute l'analyse.
        tail_contenu = tail_contenu[:CLAUSE_MAX_CHARS]
        head.append((tail_titre, tail_contenu))
        merged = head

    return merged


def _sources_from_chunks(chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for chunk in chunks:
        document = (
            str(chunk.metadata.get("document_titre") or chunk.metadata.get("source") or "")
            or "Document non precise"
        )
        numero_article = str(chunk.metadata.get("numero_article") or "") or "Article non precise"
        sources.append(
            {
                "document": document,
                "numero_article": numero_article,
                "extrait": (chunk.content or "").strip(),
            }
        )
    return sources


def analyze_clause(
    llm_client: LLMClient,
    index: int,
    titre: str,
    contenu: str,
) -> ClauseResult:
    """
    Traite un point unique du contrat : embedding -> RAG -> resume du point
    avec le contexte juridique retrouve.

    C'est ce resume (et non le texte brut du point) qui sera reinjecte dans
    le prompt final : la fenetre de contexte reste bornee.
    """
    contenu_tronque = (contenu or "").strip()[:CLAUSE_MAX_CHARS]
    try:
        clause_texte = sanitize_user_text(contenu_tronque, max_length=3000)
    except ValueError:
        # Garde-fou supplementaire : si malgre la troncature le texte nettoye
        # (espaces normalises) depasse encore la limite, on retronque plus fort
        # plutot que de laisser l'exception remonter et faire echouer TOUTE
        # l'analyse du contrat pour un seul point trop long.
        logger.warning("Point %s tronque davantage pour respecter la limite de taille.", index)
        clause_texte = sanitize_user_text(contenu_tronque[:2000], max_length=3000)

    try:
        chunks = retrieve_relevant_chunks(clause_texte, top_k=3)
    except Exception:
        logger.exception("Echec de la recuperation RAG pour le point %s", index)
        chunks = []

    prompt = build_clause_summary_prompt(
        titre_point=titre,
        contenu_point=clause_texte,
        chunks_contexte=chunks,
    )

    try:
        resume = llm_client.generate(prompt)
    except Exception:
        logger.exception("Echec de generation LLM pour le point %s", index)
        resume = (
            "Resume indisponible pour ce point (service LLM injoignable). "
            f"Contenu brut: {clause_texte[:300]}"
        )

    return ClauseResult(
        index=index,
        titre=titre,
        resume=resume.strip(),
        sources=_sources_from_chunks(chunks),
    )


def analyze_contract(
    texte_contrat: str,
    question_utilisateur: str | None = None,
) -> dict[str, Any]:
    """
    Pipeline d'analyse avancee d'un contrat, point par point.

    1) Le contrat est divise en points traites individuellement.
    2) Chaque point -> embedding -> RAG (document pertinent) -> resume LLM.
    3) Les resumes de tous les points sont assembles dans un prompt final,
       envoye au LLM pour produire la reponse consolidee.
    """
    clauses = split_contract_into_clauses(texte_contrat)
    if not clauses:
        raise ValueError("Aucun contenu exploitable n'a ete trouve dans le contrat fourni.")

    llm_client = LLMClient()

    clause_results: list[ClauseResult] = [
        analyze_clause(llm_client, index, titre, contenu)
        for index, (titre, contenu) in enumerate(clauses, start=1)
    ]

    synthesis_prompt = build_synthesis_prompt(
        points=[{"titre": r.titre, "resume": r.resume} for r in clause_results],
        question_utilisateur=question_utilisateur,
    )

    try:
        reponse_finale = llm_client.generate(synthesis_prompt)
    except Exception:
        logger.exception("Echec de generation LLM pour la synthese finale du contrat.")
        reponse_finale = (
            "Le service de generation est indisponible pour produire la synthese finale. "
            "Voici neanmoins les resumes obtenus point par point :\n\n"
            + "\n\n".join(f"{r.titre} : {r.resume}" for r in clause_results)
        )

    seen: set[tuple[str, str]] = set()
    sources_dedupliquees: list[dict[str, str]] = []
    for result in clause_results:
        for source in result.sources:
            key = (source["document"], source["numero_article"])
            if key in seen:
                continue
            seen.add(key)
            sources_dedupliquees.append(source)

    return {
        "reponse": reponse_finale.strip(),
        "sources": sources_dedupliquees,
        "points": [
            {"titre": r.titre, "resume": r.resume, "sources": r.sources}
            for r in clause_results
        ],
    }