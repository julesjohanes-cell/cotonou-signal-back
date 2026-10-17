# Où en est le back, et qui fait quoi

Le squelette fonctionne de bout en bout : un signalement peut être envoyé, publié, affiché sur la carte, suivi par son code et
traité par un agent. **Les vérifications ne sont pas toutes écrites** : c'est le travail des équipes 4, 5 et 6.

Le découpage en petites tâches avec prompts de départ est dans `docs/backlog.md`.

## Déjà fait (ne pas refaire)
- Docker, base PostGIS, migrations, catégories et services, comptes et signalements de démonstration.
- Tous les endpoints P0 et P1 du contrat (voir `docs/api-contract.md` et `/api/docs/`), le format d'erreur unique, le GeoJSON public.
- Vérification n° 1 (lien de capture) et n° 5 (distance ≤ 100 m, **modèle à suivre** : `reports/checks.py → check_distance`).
- Sécurité du webhook WhatsApp (GET de vérification et signature `X-Hub-Signature-256`), clients simulés pour l'IA et WhatsApp.
- 35 tests : `docker compose exec web python manage.py test`.

## Équipe 4 · `reports/checks.py`
- [ ] Vérification 2 · `check_photo_file` : JPEG/PNG/WebP, 8 Mo max, fichier lisible → `PHOTO_INVALID`
- [ ] Vérification 3 · `check_gps_accuracy` : précision ≤ 50 m → `GPS_INACCURATE`
- [ ] Vérification 4 · `check_zone` : téléphone dans Cotonou → `OUT_OF_ZONE` (outil prêt : `reports.geo.is_in_cotonou`)
- [ ] Un test par vérification dans `reports/tests.py` (copier `test_too_far_is_rejected…`)
- [ ] Charger le vrai polygone de Cotonou (`load_zone`) si quelqu'un fournit un GeoJSON
- [ ] `models.py` : seule équipe autorisée à modifier ; ajouter ici les champs demandés par les autres équipes

## Équipe 5 · `verification/`
- [ ] Vérification 6 · `photo_hash.check_photo_not_reused` → `PHOTO_REUSED`
- [x] Vérification 8 · `duplicates.check_duplicate` : renseigner `sub.duplicate_of` (le « +1 » est géré par `services.py`)
- [x] Vérification 7 · `vision.check_photo_content` : verdict (simulé d'abord), `PHOTO_SCREENSHOT`, `PHOTO_MISMATCH`
- [x] Brancher le vrai modèle dans `LiveVisionClient` (`VERIFY_MODE=live`), JSON strict, délai maximal
- [ ] Décision à prendre avec un mentor : que faire si le modèle ne répond pas à temps (voir `docs/verification.md`)

## Équipe 6 · `whatsapp/`
- [ ] `handlers.handle_incoming` : « Signaler » → `CaptureSession.create_for("whatsapp", …)` → message avec le lien
- [ ] Message d'aide pour tout autre texte
- [ ] Confirmation avec le code de suivi dans la discussion après la création du signalement
- [ ] `client.send_text` en mode `live` (API WhatsApp Business) ; tunnel HTTPS public pour le webhook
- [ ] Tests du handler (modèle : `whatsapp/tests.py`)

## Équipes front (1, 2, 3)
Elles consomment l'API ; voir `frontend/AGENTS.md` et `/api/docs/`. Les agents de démonstration permettent de tester l'espace mairie
tout de suite. Besoin d'un champ ou d'un endpoint en plus : le demander à l'équipe 4 et à un mentor, jamais le supposer.

## Non fait (P2)
« +1 » depuis la carte (`POST /reports/{code}/support`), statistiques (`GET /agent/stats`), journal d'audit, floutage des visages et
plaques, enregistrement des signalements rejetés, file de tâches pour l'appel à l'IA.
