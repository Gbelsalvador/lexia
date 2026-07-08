# Deploiement Lexia AI

Ce guide cible Render ou Railway avec Django, PostgreSQL et WhiteNoise.

## Variables d'environnement

Creer les variables suivantes sur la plateforme:

```env
SECRET_KEY=une-valeur-longue-et-secrete
DEBUG=False
ALLOWED_HOSTS=votre-domaine.onrender.com
CSRF_TRUSTED_ORIGINS=https://votre-domaine.onrender.com
DATABASE_URL=postgres://USER:PASSWORD@HOST:PORT/DBNAME
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
GROQ_API_KEY=
GEMINI_API_KEY=
CHROMA_PERSIST_DIRECTORY=/opt/render/project/src/chroma_db
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
RAG_MIN_RELEVANCE_SCORE=0.25
CHAT_RATE_LIMIT_COUNT=20
CHAT_RATE_LIMIT_WINDOW_SECONDS=3600
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
MAX_UPLOAD_SIZE_MB=10
MAX_CHAT_QUESTION_LENGTH=1200
```

## Commandes

Commande de build:

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

Commande de demarrage:

```bash
gunicorn config.wsgi:application
```

Ajouter `gunicorn` a `requirements.txt` si la plateforme ne l'injecte pas.

## Points de controle

- `DEBUG=False` en production.
- `ALLOWED_HOSTS` contient uniquement les domaines autorises.
- `CSRF_TRUSTED_ORIGINS` contient les origines HTTPS du site.
- La cle API LLM reste uniquement dans les variables d'environnement.
- Les PDF officiels doivent etre uploades depuis l'interface corpus (indexation asynchrone).
- ChromaDB doit etre persistant entre les redeploiements si possible.
