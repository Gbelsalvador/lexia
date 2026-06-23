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
CHROMA_PERSIST_DIRECTORY=/opt/render/project/src/chroma_db
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
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
- Le dossier ChromaDB doit etre persistant si la plateforme le permet.
- Les PDF officiels doivent etre uploades depuis l'interface admin corpus.
