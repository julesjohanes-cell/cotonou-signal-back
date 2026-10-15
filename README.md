# Cotonou Signale

Des signalements citoyens vérifiés, pour une ville plus propre.

Projet de l'atelier **Cotonou Code la nuit** (Bénin Codeurs, en partenariat avec Les Ateliers Numériques), jeudi 15 octobre. Une plateforme où les habitants de Cotonou signalent l'insalubrité avec une photo prise sur place, où chaque signalement est vérifié (position, photo, doublon), et où la mairie le traite sous les yeux du public.

## Le défi
Comment aider les habitants de Cotonou à faire remonter l'insalubrité, et la mairie à la traiter vite, avec des signalements dignes de confiance ?

## Comment ça marche
1. **Photographier sur place** : le citoyen choisit une catégorie et prend la photo avec l'appareil photo, pas la galerie.
2. **Vérifier la position** : GPS précis, à Cotonou, point placé à moins de 100 m de la personne.
3. **Vérifier la photo** : un modèle de vision confirme que la photo montre le problème déclaré et rejette les captures d'écran.
4. **Publier et traiter** : le point apparaît sur la carte, la mairie le prend en charge, le citoyen suit son avancement.

Deux portes d'entrée, une seule vérification : l'application web, ou WhatsApp (« Signaler » → lien unique valable 10 min → même page de capture → confirmation dans la discussion).

## Documentation
| Document | Contenu |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Règles pour les assistants IA et les humains (lire en premier) |
| [`docs/scope.md`](docs/scope.md) | Périmètre, priorités P0/P1/P2, critères de réussite |
| [`docs/architecture.md`](docs/architecture.md) | Architecture, choix de la stack et ses limites |
| [`docs/data-model.md`](docs/data-model.md) | Modèles, statuts, visibilité des données, catégories |
| [`docs/api-contract.md`](docs/api-contract.md) | Contrat d'API lisible (la source de vérité technique est `docs/openapi.yaml`) |
| [`docs/verification.md`](docs/verification.md) | Règles de vérification, seuils, prompt du modèle de vision |
| [`docs/whatsapp.md`](docs/whatsapp.md) | Parcours WhatsApp et webhook |
| [`docs/team-workflow.md`](docs/team-workflow.md) | Façon de travailler en équipe avec l'IA |
| [`docs/dev-environment.md`](docs/dev-environment.md) | Docker au quotidien : rechargement automatique, quand relancer, dépannage |
| [`docs/tasks.md`](docs/tasks.md) | Ce qui est fait et ce qui reste à faire, par équipe |
| [`README-IA.md`](README-IA.md) | Quel fichier de règles pour quel outil d'IA |

## Démarrer
```bash
docker compose up           # lance la base PostGIS et l'API (le fichier .env est facultatif)
```
Au premier lancement, Docker télécharge les images : prévoir plusieurs minutes. Ensuite, **pas besoin d'arrêter ni de relancer
à chaque modification** : le code est rechargé automatiquement (détails dans [`docs/dev-environment.md`](docs/dev-environment.md)).

| Quoi | Adresse |
| --- | --- |
| Documentation interactive de l'API | http://localhost:8000/api/docs/ |
| Espace mairie (admin Django) | http://localhost:8000/admin/ · `admin` / `admin1234` · agents `agent.dechets`… / `agent1234` |
| Contrat OpenAPI | [`docs/openapi.yaml`](docs/openapi.yaml) |

Les comptes et les signalements « [démo] » sont fictifs et réservés au développement.
Tests : `docker compose exec web python manage.py test`.

## Structure
```text
backend/            Django + DRF + GeoDjango
  config/           réglages (seuils des règles), format d'erreur, URLs
  reports/          modèles, API publique et agent, vérifications 1 à 5 (checks.py)
  verification/     pipeline des vérifications, empreinte, vision, doublons (6 à 8)
  whatsapp/         webhook, signature, client, traitement des messages
frontend/           Next.js (capture, carte, espace mairie) : à venir
docs/               documentation et openapi.yaml
docker-compose.yml  base PostGIS + API
```

## Équipe d'animation
- Johanes : cadre de travail et IA
- Noé DJROTON : mentor front-end (Next.js)
- Jean FLORENTIN : mentor back-end (Python, Django)
