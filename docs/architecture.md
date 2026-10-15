# Architecture et choix de la stack

## Vue d'ensemble
```text
Citoyen (navigateur mobile) ──► Next.js ──► API Django (DRF) ──► PostgreSQL + PostGIS
                                                  │
Citoyen (WhatsApp) ──► Meta ──► webhook Django ───┤──► modèle de vision (vérification photo)
                                                  └──► API WhatsApp Business (réponses)
Agent de la mairie ──► Next.js (espace mairie) ──► API Django (rôles par service)
```

## Stack retenue
| Couche | Choix | Rôle |
| --- | --- | --- |
| Front | Next.js (TypeScript) | Parcours de signalement, carte de Cotonou, page de capture WhatsApp, espace mairie |
| Back | Python + Django + DRF | API des signalements, vérification GPS et IA, webhook WhatsApp, rôles et journal d'audit |
| Données | PostgreSQL + PostGIS (GeoDjango) | Stockage et requêtes géographiques |
| Carte | MapLibre + OpenStreetMap | Affichage des signalements |
| IA | Modèle de vision | Vérification de la photo |
| Messagerie | API WhatsApp Business | Deuxième porte d'entrée |

## Pourquoi Django pour ce projet
1. **L'espace mairie est presque gratuit.** L'admin Django donne liste, filtres par catégorie et statut, modification et carte (widget GeoDjango) sans écrire de front.
2. **Le géospatial est natif.** Point dans le polygone de Cotonou, distance entre deux points (règle des 100 m), recherche de doublons (`dwithin`), sortie GeoJSON.
3. **Rôles et permissions inclus.** Groupes par service (assainissement, éclairage, police municipale) : le routage des catégories est de la configuration, pas du code.
4. **Un cadre strict, adapté au travail avec l'IA.** Convention forte (modèles, serializers, vues, URLs) : l'IA génère du code cohérent et les débutants savent où écrire.
5. **Python est le langage de l'IA et de l'image.** SDK des modèles de vision, Pillow pour le floutage, `hashlib` pour l'empreinte, lecture EXIF.
6. **Contrat d'API automatique.** DRF + drf-spectacular génèrent le schéma OpenAPI et une page de test interactive.

## Comparaison avec d'autres stacks (sur ce projet)
| Stack | Ce qu'elle apporte ici | Ce qui manque ou coûte ici |
| --- | --- | --- |
| Django + DRF + PostGIS (retenu) | Admin, auth, géo, ORM, migrations, OpenAPI | Deux langages ; GeoDjango demande GDAL/GEOS |
| Node (Express / NestJS) + Prisma | Un seul langage avec Next.js, types partagés | Pas d'admin, pas de rôles prêts, requêtes géo en SQL brut |
| FastAPI + SQLAlchemy | Rapide, async, doc auto | Admin, auth et géo à assembler |
| Laravel (PHP) | Productif, panneaux d'admin | Géospatial moins natif, écosystème IA/image moins direct |
| Supabase / Firebase | Démarrage très rapide, auth et stockage inclus ; Supabase propose PostGIS | Logique de vérification dans des fonctions serverless ; données hébergées hors du Bénin ; Firestore sans requêtes géo natives |

## Limites assumées
- **Deux langages** : compensé par le contrat OpenAPI et un `docker compose` qui lance tout.
- **GeoDjango est difficile à installer en local** (GDAL/GEOS, surtout sous Windows et macOS) : on impose l'image Docker `postgis/postgis` et un conteneur Django. Personne n'installe quoi que ce soit en local.
- **Django est synchrone par défaut** : un appel au modèle de vision prend des secondes. Pour la démonstration, appel direct avec délai maximal ; ensuite, file de tâches (Celery) et statut « en vérification ».

## Contrat entre front et back
- Le fichier `docs/openapi.yaml` est généré par le code (drf-spectacular) et exposé sur `/api/docs/`.
- Un serveur factice peut être lancé à partir de ce fichier (par exemple `npx @stoplight/prism-cli mock docs/openapi.yaml`) pour que le front avance sans attendre le back.
- Chaque code d'erreur doit avoir une réponse d'exemple, pour que le front puisse construire tous les écrans de rejet.
