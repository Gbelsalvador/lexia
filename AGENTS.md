# AGENTS.md — Système RAG pour la vulgarisation du Code du Travail (PME de Kinshasa)

## Contexte du projet
Projet de fin d'année (PFE). Sujet : "Analyse et conception d'un système de
génération augmentée par récupération (RAG) pour la vulgarisation du Code
du Travail : Cas des PME de la ville de Kinshasa".

## Contraintes techniques strictes
- 100% Django (backend ET frontend). Pas de React/Vue/Angular séparé.
  Frontend = Django Templates + Bootstrap 5 (CDN) + JS vanilla (fetch API).
- Base de données : PostgreSQL en prod, SQLite acceptable en dev local.
- Stockage vectoriel : ChromaDB en mode persisté localement (PersistentClient).
- Embeddings : sentence-transformers, modèle
  `paraphrase-multilingual-MiniLM-L12-v2` (gratuit, local, fonctionne en français).
- Génération de texte (LLM) : API externe configurable via `.env`
  (`LLM_PROVIDER=openai`, `groq` ou `gemini`). Interface `LLMClient` pour
  basculer de fournisseur sans réécrire le code.
- Auth : système Django natif (AbstractUser étendu), rôles PME / ADMIN.

## Structure du projet (cible)
```
config/                # settings Django
accounts/               # auth, modèle Utilisateur (PME/Admin)
corpus/                 # ingestion et indexation du Code du Travail
chatbot/                # conversations, vues de chat
dashboard/               # statistiques admin
rag_engine/             # module Python pur : embeddings, vector_store,
                          retriever, prompt_builder, llm_client, pipeline
templates/
static/
.env / .env.example
requirements.txt
```

## Commandes utiles (à utiliser pour vérifier ton travail)
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

## Règles de travail pour l'agent
1. Travaille en mode "suggest" / propose les diffs : ne passe pas en
   full-auto sans validation explicite de ma part pour les étapes
   touchant plus de 3-4 fichiers.
2. Avant de coder une étape, donne un court plan (fichiers à créer/modifier)
   et attends ma confirmation si l'étape est grosse.
3. Avance étape par étape selon le découpage ci-dessous. Ne crée pas de
   fichiers appartenant à une étape future avant que la précédente soit validée.
4. Après chaque étape : lance `python manage.py check` et/ou
   `python manage.py test`, corrige les erreurs avant de t'arrêter.
5. Utilise un environnement virtuel (venv) et garde requirements.txt à jour.
6. Les clés API (OPENAI_API_KEY) vont uniquement dans `.env` (django-environ),
   jamais en dur dans le code, jamais committées.
7. Code commenté en français, conventions PEP8, type hints sur les
   fonctions du module rag_engine.
8. Ne jamais inventer le contenu du Code du Travail congolais : le texte
   source officiel sera fourni en PDF dans /corpus_source/.
9. Fais un commit Git avec un message clair à la fin de chaque étape validée.

## Découpage en étapes (à suivre dans l'ordre)
1. Initialisation du projet Django (apps, settings, .env, requirements.txt, base.html)
2. App accounts (modèle Utilisateur, inscription/connexion PME)
3. App corpus (modèles, pipeline d'ingestion PDF → chunks → ChromaDB)
4. Module rag_engine (embeddings, vector_store, retriever, prompt_builder, llm_client, pipeline)
5. App chatbot (conversation, vue API chat, interface JS fetch)
6. App dashboard (statistiques admin, graphiques Chart.js)
7. Sécurité, tests unitaires, finitions, préparation au déploiement

## Statut actuel
(Mets à jour cette section après chaque étape validée.)
- [x] Étape 1 — Initialisation
- [x] Étape 2 — accounts
- [x] Étape 3 — corpus
- [x] Étape 4 — rag_engine
- [x] Étape 5 — chatbot
- [x] Étape 6 — dashboard
- [x] Étape 7 — sécurité/tests