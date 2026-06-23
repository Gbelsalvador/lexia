# Lexia AI

Assistant RAG Django pour vulgariser le Code du Travail de la RDC aupres des PME de Kinshasa.

Le projet utilise Django pour le backend et le frontend, SQLite en local, ChromaDB pour la recherche vectorielle, `sentence-transformers` pour les embeddings locaux et un LLM externe pour generer les reponses.

## Prerequis

- Python 3.12 recommande
- PowerShell sous Windows
- Une cle API OpenAI ou Gemini
- Le PDF officiel du Code du Travail a indexer

## Installation locale

Depuis le dossier du projet :

```powershell
cd "C:\Users\gb\Documents\project python\lexia-ai"
```

Activer le venv existant :

```powershell
.\.venv\Scripts\Activate.ps1
```

Si le venv n'existe pas :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration `.env`

Creer un fichier `.env` a partir de `.env.example` :

```powershell
Copy-Item .env.example .env
```

Pour travailler en local, utiliser par exemple :

```env
SECRET_KEY=change-me-in-local-env
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=
DATABASE_URL=sqlite:///db.sqlite3

LLM_PROVIDER=openai
OPENAI_API_KEY=votre-cle-openai
GEMINI_API_KEY=

CHROMA_PERSIST_DIRECTORY=./chroma_db
EMBEDDING_MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2

SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0

MAX_UPLOAD_SIZE_MB=10
MAX_CHAT_QUESTION_LENGTH=1200
```

Ne jamais commit le fichier `.env`.

## Base de donnees

Appliquer les migrations :

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Creer un compte administrateur :

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Ensuite, dans l'admin Django, donner le role `ADMIN` a ce compte si necessaire.

## Lancer le serveur

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Ouvrir ensuite :

- Accueil : http://127.0.0.1:8000/
- Connexion : http://127.0.0.1:8000/comptes/connexion/
- Chatbot : http://127.0.0.1:8000/chatbot/
- Corpus admin : http://127.0.0.1:8000/corpus/
- Dashboard admin : http://127.0.0.1:8000/dashboard/
- Admin Django : http://127.0.0.1:8000/admin/

## Indexer le Code du Travail

Option 1, via l'interface :

1. Se connecter avec un compte `ADMIN`.
2. Aller sur http://127.0.0.1:8000/corpus/upload/
3. Uploader le PDF officiel.
4. Attendre la fin de l'extraction, du chunking, des embeddings et de l'indexation ChromaDB.

Option 2, via une commande :

```powershell
.\.venv\Scripts\python.exe manage.py indexer_corpus ".\corpus_source\code_travail.pdf" --titre "Code du Travail RDC" --username admin
```

Le premier chargement du modele `sentence-transformers` peut prendre du temps.

## Utiliser le chatbot

1. Creer ou connecter un compte PME.
2. Aller sur http://127.0.0.1:8000/chatbot/
3. Poser une question en francais.
4. Les sources citees apparaissent sous chaque reponse.
5. Utiliser les boutons de feedback pour noter la reponse.

Si le LLM est indisponible, le message utilisateur est sauvegarde et une reponse de fallback est affichee.

## Dashboard admin

Le dashboard est reserve aux utilisateurs `ADMIN`.

Il affiche :

- Nombre total de PME inscrites
- Nombre de questions posees
- Questions des 7 derniers jours
- Taux de satisfaction
- Nombre de documents et chunks indexes
- Graphiques Chart.js
- Liste des PME avec recherche
- Detail des conversations pour audit

## Tests et verification

Commandes utiles :

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

## Depannage

Si `python` n'est pas reconnu, utiliser toujours :

```powershell
.\.venv\Scripts\python.exe
```

Si le chatbot indique que le service LLM est indisponible :

- Verifier `OPENAI_API_KEY` ou `GEMINI_API_KEY` dans `.env`.
- Verifier `LLM_PROVIDER`.
- Relancer le serveur apres modification du `.env`.

Si l'indexation PDF echoue :

- Verifier que le fichier est un vrai PDF.
- Verifier que sa taille ne depasse pas `MAX_UPLOAD_SIZE_MB`.
- Verifier que le PDF contient du texte extractible.

Si le modele d'embeddings est lent au premier lancement :

- C'est normal au premier chargement.
- Le modele `paraphrase-multilingual-MiniLM-L12-v2` est telecharge/cache par `sentence-transformers`.

## Deploiement

Voir [DEPLOYMENT.md](DEPLOYMENT.md).
