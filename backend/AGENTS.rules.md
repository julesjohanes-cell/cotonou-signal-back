# Règles du dépôt Cotonou Signale (Prioritaires pour le code métier backend)
Source : https://github.com/julesjohanes-cell/cotonou-signal-back/blob/main/backend/AGENTS.md

Contrat : docs/openapi.yaml
- Structure :
  - config/ : settings.py, errors.py, URLs racine
  - reports/ : modèles, serializers, vues, services.py, checks.py, geo.py
  - verification/ : pipeline.py, photo_hash.py, vision.py, duplicates.py, submission.py
  - whatsapp/ : handlers.py, client.py, signature.py, views.py
- Vérifications ordonnées d'un signalement :
  1. Jeton capture valide (10 min)
  2. Photo lisible (max 8 Mo)
  3. Précision GPS ≤ 50 m
  4. Position téléphone dans Cotonou
  5. Distance point / téléphone ≤ 100 m
  6. Empreinte SHA-256 de la photo
  7. Modèle de vision IA (confiance ≥ 0,6)
  8. Doublon : même catégorie, < 30 m, actif ≤ 30 jours
- Format d'erreur strict :
  {"error": {"code": "...", "message": "...", "details": {}}}
- Géographie GeoDjango : Point(lng, lat, srid=4326) avec longitude en premier !
