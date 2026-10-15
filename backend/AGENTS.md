# Back-end · Django (règles pour les assistants IA)

Complète le `AGENTS.md` de la racine, qui reste prioritaire. Contrat : `docs/openapi.yaml`.

## Structure
- `config/` : `settings.py` (réglages ET seuils des règles), `errors.py` (format d'erreur, `ApiError` et `Rejection`), URLs racine.
- `reports/` (équipe 4) : modèles, serializers, vues, `services.py` (création d'un signalement), `checks.py` (vérifications 1 à 5), `geo.py` (outils géographiques).
- `verification/` (équipe 5) : `pipeline.py` (liste `STEPS`), `photo_hash.py` (6), `vision.py` (7), `duplicates.py` (8), `submission.py`.
- `whatsapp/` (équipe 6) : `handlers.py` (traitement des messages), `client.py` (envoi, mode simulé), `signature.py`, `views.py` (webhook).
- Une vérification = une fonction `check_xxx(sub)` qui ne renvoie rien et lève `Rejection("CODE")` si elle refuse. Modèle à suivre : `reports/checks.py → check_distance`. Suivi des tâches : `docs/tasks.md`.

## Commandes (toujours dans Docker)
```bash
docker compose up
docker compose exec web python manage.py makemigrations   # équipe 4 uniquement
docker compose exec web python manage.py migrate
docker compose exec web python manage.py loaddata categories
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py load_zone /docs/cotonou.geojson   # polygone de Cotonou
docker compose exec web python manage.py spectacular --file /docs/openapi.yaml
docker compose exec web python manage.py test
```
Documentation interactive : `/api/docs/`. Schéma : `/api/schema/` (drf-spectacular).
Le code est rechargé automatiquement : pas besoin de relancer Docker à chaque modification (voir `docs/dev-environment.md`).

## Règles Django et API
- L'API vit sous `/api/v1/`. Vues avec DRF (`APIView` ou `ViewSet`), validation dans les serializers, logique métier dans des fonctions simples (pas dans les vues).
- Toute erreur passe par un gestionnaire d'exceptions unique qui produit `{"error": {"code", "message", "details"}}` avec les codes du contrat.
- Les seuils (50 m, 100 m, 30 m, 0,6, 10 min, 8 Mo) vivent dans `config/settings.py` (section « Règles métier »), lus avec `from django.conf import settings`. Jamais en dur ailleurs.
- Configuration par variables d'environnement (`.env`). Jamais de secret dans le code.
- Ne pas ajouter de bibliothèque sans accord. Ne pas changer la version de Django.

## Géographie (GeoDjango)
- Créer un point avec la longitude en premier : `Point(lng, lat, srid=4326)`. Vérifier l'ordre à chaque fois.
- Champs en `geography=True` : les distances sont en mètres. Utiliser `D(m=30)` avec `dwithin` ou `Distance`, et vérifier le résultat avec un test chiffré.
- Le polygone de Cotonou est chargé en base (modèle de zone) ; en secours, une boîte englobante provisoire clairement marquée.
- Sortie GeoJSON pour la carte : propriétés publiques seulement (`tracking_code`, `category`, `status`, `support_count`, `photo_url`, `created_at`).

## Modèles et migrations
- Seule l'équipe 4 modifie `reports/models.py` et crée des migrations. Ne jamais éditer une migration existante. En cas de conflit de migrations, signaler, ne pas improviser.
- Les 8 catégories et leurs services sont des fixtures (`categories`).

## Vérifications et IA
- `VERIFY_MODE=mock|live`. En `mock`, le verdict est prévisible (accepte tout sauf un fichier nommé `screenshot`). Le code ne doit jamais dépendre d'une clé réelle pour démarrer.
- La réponse du modèle de vision est du JSON strict ; toute réponse mal formée est traitée comme un échec, jamais devinée. Délai maximal de 15 s.
- Le verdict IA et sa raison ne sont jamais renvoyés au public.
- Empreinte : SHA-256 du contenu de la photo (`hashlib`), stockée dans `photo_sha256`.

## WhatsApp
- `GET /api/v1/webhooks/whatsapp` : répondre avec `hub.challenge` si `hub.verify_token` est correct.
- `POST /api/v1/webhooks/whatsapp` : vérifier `X-Hub-Signature-256` (HMAC-SHA256 du corps brut avec le secret de l'application, comparaison avec `hmac.compare_digest`), répondre `200` tout de suite, puis traiter.
- Message « signaler » (minuscules, sans accents) : créer une `CaptureSession` de 10 min et répondre avec le lien `<FRONT_URL>/capture/<token>`.
- `WHATSAPP_MODE=mock|live` : en `mock`, les messages sortants sont écrits dans les logs au lieu d'être envoyés.
- Ne jamais journaliser un numéro de téléphone en clair.

## Tests
- Un test par code d'erreur du contrat (`TOO_FAR`, `OUT_OF_ZONE`, `TOKEN_EXPIRED`, …) et un test du parcours réussi de `POST /reports`.
- Un test qui vérifie que le GeoJSON public ne contient aucun champ privé.
