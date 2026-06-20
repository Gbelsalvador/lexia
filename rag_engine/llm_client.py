from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """Réponse normalisée retournée par un fournisseur LLM."""

    content: str
    provider: str
    model: str


class LLMClient:
    """Interface pour changer de fournisseur LLM sans réécrire le pipeline."""

    def generate(self, prompt: str) -> LLMResponse:
        """Génère une réponse à partir d'un prompt augmenté."""
        raise NotImplementedError
