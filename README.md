# SandBos — Monorepo (Next.js + Django REST Framework)

Projet fullstack configuré avec **Dexty 3.5.1**.

## Architecture du projet

```text
SandBos/
├── frontend/                  # Next.js 15+ (TypeScript, Tailwind CSS, App Router)
│   ├── src/app/              # Pages et layout Next.js
│   ├── src/lib/api.ts        # Client API pour communiquer avec Django
│   └── .env.local            # Variables d'environnement frontend (NEXT_PUBLIC_API_URL)
├── backend/                   # Python 3.12 + Django REST Framework
│   ├── config/               # Settings Django, URLs principales et configuration CORS
│   ├── api/                  # Application API REST (endpoints /health/, /features/, etc.)
│   ├── venv/                 # Environnement virtuel Python
│   ├── requirements.txt      # Dépendances Python
│   └── .env                  # Variables d'environnement backend (DJANGO_SECRET_KEY, DEBUG, etc.)
├── .project-memory/           # Mémoire de projet Dexty (MAP.md, STATE.md, etc.)
├── agents/                    # Fiches des 8 agents chefs Dexty
└── package.json               # Commandes globales du monorepo
```

## Démarrage rapide

### 1. Démarrer le Backend (Django)
```bash
# Via le script monorepo :
npm run dev:backend

# Ou directement :
cd backend
venv/bin/python manage.py runserver 8000
```
L'API est accessible sur `http://localhost:8000/api/` :
- `http://localhost:8000/api/health/`
- `http://localhost:8000/api/features/`

### 2. Démarrer le Frontend (Next.js)
```bash
# Via le script monorepo :
npm run dev:frontend

# Ou directement :
cd frontend
npm run dev
```
Le frontend est accessible sur `http://localhost:3000`.

### 3. Autres commandes utiles
```bash
# Vérifier la configuration Django
npm run check:backend

# Appliquer les migrations de BDD
npm run migrate:backend

# Compiler le frontend
npm run build:frontend
```
