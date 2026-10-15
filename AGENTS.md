# Cotonou Signale · Règles pour les assistants IA

Ce fichier est la source unique des règles du projet. Il est lu par les outils d'IA de codage et par les humains. En cas de conflit avec un autre fichier de règles, celui-ci gagne. Les dossiers `backend/` et `frontend/` ont leur propre `AGENTS.md` pour les détails techniques.

## Le projet
Plateforme de signalement citoyen d'insalubrité à Cotonou (Bénin). Un citoyen signale un problème avec une photo prise sur place et sa position ; le serveur vérifie la position, la photo et les doublons ; la mairie traite le signalement et le citoyen suit son avancement. Deux entrées : application web et WhatsApp, avec la même vérification.

Contexte : atelier de 2 h de développement, équipes de niveaux très variés. On préfère un parcours complet et simple (signaler, vérifier, voir sur la carte, changer le statut) à beaucoup de fonctions à moitié finies.

## Stack
- Back : Python 3.12, Django, Django REST Framework, GeoDjango, PostgreSQL + PostGIS (Docker)
- Front : Next.js (TypeScript), MapLibre + OpenStreetMap
- Messagerie : API WhatsApp Business (webhook côté back)
- IA : modèle de vision, appelé uniquement par le back
- Tout se lance avec `docker compose up`. Personne n'installe GDAL, PostGIS ou une base en local.

## Source de vérité
- Le contrat d'API est `docs/openapi.yaml`. Ne jamais inventer un endpoint, un champ, un statut ou un code d'erreur absent du contrat.
- Si le contrat est ambigu ou insuffisant, ne devine pas : propose la modification, signale-la clairement, et attends l'accord d'un humain.
- Le contrat est gelé à 20h20 le jeudi 15 octobre. Après, on ajoute (champ facultatif, nouvel endpoint), on ne renomme ni ne supprime rien.
- Documentation de référence à lire selon la tâche : `docs/scope.md` (priorités), `docs/architecture.md` (stack), `docs/data-model.md` (modèles et statuts), `docs/api-contract.md` (endpoints et erreurs), `docs/verification.md` (règles et seuils), `docs/whatsapp.md` (webhook), `docs/team-workflow.md` (façon de travailler), `docs/tasks.md` (ce qui est fait et à faire par équipe), `docs/backlog.md` (petites tâches et prompts de départ), `docs/dev-environment.md` (Docker au quotidien).

## Conventions
- Noms de champs en `snake_case`, dates en ISO 8601 UTC.
- Toute erreur de l'API : `{"error": {"code": "...", "message": "...", "details": {}}}`. `message` est en français et lisible par un citoyen.
- Coordonnées dans les champs de formulaire : toujours nommées (`point_lat`, `point_lng`, `device_lat`, `device_lng`).
- GeoJSON : `[longitude, latitude]`. C'est le piège numéro un, vérifie-le à chaque fois.
- Textes visibles par l'utilisateur en français.

## Règles métier (vérifications d'un signalement, dans cet ordre)
1. Jeton de capture valide, non expiré (10 min), non utilisé.
2. Photo lisible, JPEG, PNG ou WebP, 8 Mo maximum.
3. Précision GPS du téléphone ≤ 50 m.
4. Position du téléphone dans Cotonou.
5. Distance entre le point du problème et le téléphone ≤ 100 m.
6. Empreinte SHA-256 de la photo jamais vue.
7. Modèle de vision : la photo montre la catégorie déclarée et n'est pas une capture d'écran (confiance ≥ 0,6).
8. Doublon : même catégorie, moins de 30 m, signalement actif des 30 derniers jours : on fusionne et on incrémente `support_count`.

Les seuils vivent dans un seul fichier de réglages, jamais en dur dans plusieurs endroits.

## Vie privée et sécurité
- Ne jamais exposer dans l'API publique : `reporter_location`, `reporter_ref`, `distance_m`, `ai_verdict`.
- Ne jamais stocker un numéro de téléphone en clair : seulement `reporter_ref` (HMAC du numéro).
- Les secrets (clés d'API, jetons, secret WhatsApp) vivent dans `.env`, jamais dans le code, un test, un prompt ou un commit. Maintenir `.env.example` sans valeurs réelles.
- On signale des lieux de l'espace public, jamais des individus. Aucune donnée personnelle réelle dans les données de démonstration.
- Le webhook WhatsApp doit vérifier la signature `X-Hub-Signature-256` avant de traiter quoi que ce soit.

## Interdits
- Pas de nouvelle dépendance sans accord d'un mentor.
- Pas de refactorisation, de renommage ni de réécriture complète d'un fichier : diff minimal, limité à la tâche.
- Ne pas modifier un fichier hors du périmètre indiqué dans la tâche.
- Ne jamais modifier une migration existante.
- Ne pas désactiver une vérification ou un test pour « faire passer » un résultat.
- Ne pas inventer une bibliothèque, une option ou une API : si tu n'es pas sûr qu'elle existe, dis-le.

## Façon de travailler
1. Lis ce fichier, celui du dossier concerné et la partie du contrat qui s'applique.
2. Donne d'abord un plan en 5 lignes maximum et attends l'accord avant de coder.
3. Une tâche petite à la fois. Termine toujours par la commande qui permet de tester (`curl`, test, page `/api/docs/`).
4. Explique brièvement ce que tu as changé et pourquoi, en français simple. Si la personne débute, explique davantage.
5. Si une approche échoue deux fois, arrête-toi : donne l'erreur exacte, ce que tu as essayé, et demande de l'aide plutôt que de réessayer à l'aveugle.
6. Un commit par tâche terminée, message court et clair. La branche `main` doit toujours démarrer avec `docker compose up`.

## Zones et propriétaires (à confirmer avec les organisateurs)
| Zone | Équipe |
| --- | --- |
| `frontend/` capture citoyen | 1 |
| `frontend/` carte et suivi | 2 |
| `frontend/` espace mairie | 3 |
| `backend/reports/` modèles, création, vérifications 1 à 5 (`checks.py`), GeoJSON | 4 (seule équipe qui modifie `models.py` et crée des migrations) |
| `backend/verification/` vérifications 6 à 8 : empreinte, modèle de vision, doublons | 5 |
| `backend/whatsapp/` webhook, sessions de capture, messages | 6 |

Une équipe qui a besoin d'un nouveau champ de modèle le demande à l'équipe 4, elle ne l'ajoute pas elle-même.
