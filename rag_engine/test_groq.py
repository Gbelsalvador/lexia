import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def load_groq_api_key() -> str:
    """Recupere la cle Groq depuis la variable d'environnement ou le fichier .env."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if api_key:
        return api_key

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "GROQ_API_KEY":
                value = value.strip().strip('"').strip("'")
                if value:
                    return value

    raise RuntimeError(
        "Aucune cle GROQ_API_KEY trouvee. Definissez-la dans votre environnement ou dans .env."
    )


def test_groq_key(api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
    """Teste la cle Groq en envoyant une requete minimale a l'API."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Tu reponds en francais"},
            {"role": "user", "content": "parle moi de la durée du contrat selon le code de travail en rdc"},
        ],
        "temperature": 0.2,
    }

    request = Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            print("OK: la cle Groq fonctionne.")
            print(f"Modele utilise: {model}")
            print(f"Reponse: {content}")
    except HTTPError as exc:
        print(f"ERREUR HTTP {exc.code}")
        print(exc.read().decode("utf-8", errors="ignore"))
        sys.exit(1)
    except URLError as exc:
        print(f"ERREUR RESEAU: {exc}")
        sys.exit(1)
    except Exception as exc:  # pragma: no cover - depend du runtime
        print(f"ERREUR INATTENDUE: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        api_key = load_groq_api_key()
    except RuntimeError as exc:
        print(exc)
        sys.exit(1)

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    test_groq_key(api_key, model=model)
