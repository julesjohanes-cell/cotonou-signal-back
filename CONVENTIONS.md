# Cotonou Signale · conventions (Aider et outils similaires)

Les règles complètes du projet sont dans `AGENTS.md` à la racine (détails dans `backend/AGENTS.md` et `frontend/AGENTS.md`). Le fichier `.aider.conf.yml` les charge en lecture seule.

Essentiel :
- Le contrat `docs/openapi.yaml` est la seule source de vérité : n'invente ni champ, ni endpoint, ni code d'erreur.
- Donne un plan en 5 lignes et attends l'accord avant de coder.
- Diff minimal, dans le périmètre de la tâche, sans nouvelle dépendance.
- GeoJSON : `[longitude, latitude]`. Aucun champ privé dans l'API publique.
