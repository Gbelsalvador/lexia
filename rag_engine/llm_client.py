from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


@dataclass(frozen=True)
class LLMResponse:
    """Reponse normalisee retournee par un fournisseur LLM."""

    content: str
    provider: str
    model: str


class LLMClient:
    """
    Client LLM avec interface stable pour changer de fournisseur.

    Le fournisseur est pilote par `settings.LLM_PROVIDER`.
    """

    def __init__(
        self,
        provider: str | None = None,
        openai_model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.provider = (provider or settings.LLM_PROVIDER or "openai").lower().strip()
        self.openai_model = openai_model or self._default_model_for_provider()
        self.timeout = timeout

    def _default_model_for_provider(self) -> str:
        """Retourne le modele par defaut adapte au fournisseur choisi."""
        if self.provider == "groq":
            return "llama-3.3-70b-versatile"
        return "gpt-4o-mini"

    def generate(self, prompt: str) -> str:
        """
        Genere une reponse textuelle a partir du prompt fourni.

        Args:
            prompt: Prompt final construit par le pipeline RAG.

        Returns:
            Texte de reponse genere par le LLM.
        """
        cleaned_prompt = (prompt or "").strip()
        if not cleaned_prompt:
            raise ValueError("Le prompt ne peut pas etre vide.")

        if self.provider == "openai":
            return self._generate_openai(cleaned_prompt).content

        if self.provider == "groq":
            try:
                return self._generate_groq(cleaned_prompt).content
            except RuntimeError:
                return self._generate_openai(cleaned_prompt).content

        if self.provider == "gemini":
            return self._generate_gemini(cleaned_prompt).content

        raise RuntimeError(
            f"Fournisseur LLM non supporte: '{self.provider}'. "
            "Utilisez 'openai', 'groq' ou 'gemini'."
        )

    def _generate_openai(self, prompt: str) -> LLMResponse:
        """Implementation OpenAI (openai>=1.0) avec gestion d'erreurs explicite."""
        api_key = (settings.OPENAI_API_KEY or "").strip()
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY manquante. Configurez la cle dans le fichier .env."
            )

        try:
            from openai import (
                APIConnectionError,
                APIStatusError,
                APITimeoutError,
                OpenAI,
                RateLimitError,
            )
        except ImportError as exc:
            raise RuntimeError("Le package openai est requis pour le fournisseur OpenAI.") from exc

        client = OpenAI(api_key=api_key, timeout=self.timeout)

        try:
            response = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu reponds en francais clair et tu respectes "
                            "strictement les consignes du prompt utilisateur."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            content = (response.choices[0].message.content or "").strip()
            if not content:
                raise RuntimeError("OpenAI a retourne une reponse vide.")

            return LLMResponse(content=content, provider="openai", model=self.openai_model)
        except RateLimitError as exc:
            raise RuntimeError(
                "Quota OpenAI depasse ou limite de requetes atteinte. "
                "Veuillez verifier votre plan/facturation puis reessayer."
            ) from exc
        except APITimeoutError as exc:
            raise RuntimeError(
                "Timeout OpenAI: le service met trop de temps a repondre. "
                "Veuillez reessayer."
            ) from exc
        except APIConnectionError as exc:
            raise RuntimeError(
                "Erreur de connexion a OpenAI. Verifiez votre reseau puis reessayez."
            ) from exc
        except APIStatusError as exc:
            if exc.status_code in {401, 403}:
                raise RuntimeError(
                    "Cle OpenAI invalide ou non autorisee. Verifiez OPENAI_API_KEY."
                ) from exc
            raise RuntimeError(
                f"Erreur OpenAI (HTTP {exc.status_code}). Veuillez reessayer plus tard."
            ) from exc
        except Exception as exc:  # pragma: no cover - defense generale
            raise RuntimeError("Erreur inattendue lors de l'appel OpenAI.") from exc

    def _generate_groq(self, prompt: str) -> LLMResponse:
        """Implementation Groq via l'API OpenAI-compatible de Groq."""
        api_key = (settings.GROQ_API_KEY or "").strip()
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY manquante. Configurez la cle dans le fichier .env."
            )

        payload = {
            "model": self.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Tu reponds en francais clair et tu respectes "
                        "strictement les consignes du prompt utilisateur."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        request = Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
        except HTTPError as exc:
            status_code = exc.code
            if status_code in {401, 403}:
                raise RuntimeError("Cle Groq invalide ou non autorisee. Verifiez GROQ_API_KEY.") from exc
            raise RuntimeError(
                f"Erreur Groq (HTTP {status_code}). Veuillez reessayer plus tard."
            ) from exc
        except URLError as exc:
            raise RuntimeError("Erreur de connexion a Groq. Verifiez votre reseau puis reessayez.") from exc
        except TimeoutError as exc:
            raise RuntimeError("Timeout Groq: le service met trop de temps a repondre.") from exc
        except Exception as exc:  # pragma: no cover - defense generale
            raise RuntimeError("Erreur inattendue lors de l'appel Groq.") from exc

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Groq a retourne une reponse vide.")

        content = (choices[0].get("message", {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("Groq a retourne une reponse vide.")

        return LLMResponse(content=content, provider="groq", model=self.openai_model)

    def _generate_gemini(self, prompt: str) -> LLMResponse:
        """
        Implementation Gemini minimale pour faciliter un futur basculement.

        Cette branche reste optionnelle, activee uniquement si LLM_PROVIDER=gemini.
        """
        api_key = (settings.GEMINI_API_KEY or "").strip()
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY manquante. Configurez la cle dans le fichier .env."
            )

        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError("Le package google-generativeai est requis pour Gemini.") from exc

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            response = model.generate_content(prompt)
            content = (getattr(response, "text", "") or "").strip()
            if not content:
                raise RuntimeError("Gemini a retourne une reponse vide.")

            return LLMResponse(content=content, provider="gemini", model="gemini-1.5-flash")
        except Exception as exc:  # pragma: no cover - depend du runtime externe
            raise RuntimeError("Erreur lors de l'appel Gemini.") from exc
