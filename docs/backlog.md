# Backlog du back-end : petites tâches et prompts de départ

Chaque tâche est faite pour tenir en 15 à 30 minutes avec une IA, dans **un seul fichier** (ou deux), avec **un critère de fin vérifiable**. Les tâches d'une même équipe sont indépendantes sauf mention « après B-x ». Les équipes ne se marchent pas dessus : une équipe = ses fichiers (voir `AGENTS.md`).

## Comment utiliser ce document
1. Prendre la première tâche libre de son équipe, la cocher dans `docs/tasks.md`.
2. Copier le prompt, **adapter la ligne « Tâche »**, le coller dans l'outil d'IA.
3. Lire le plan de l'IA (5 lignes), dire oui ou corriger, puis seulement générer le code.
4. Lancer la commande de test, puis commit. Une tâche = un commit.

### Gabarit de prompt (template exemple)
```text
Contexte : lis AGENTS.md, backend/AGENTS.md et docs/verification.md.
Tâche : <une phrase>
Modèle à suivre : <fonction ou test existant>
Fichiers : <fichiers autorisés>. Ne modifie rien d'autre.
Critère de fin : <ce qui doit être vrai>
Contraintes : aucune dépendance ajoutée, seuils lus dans settings, pas de refactorisation.
D'abord ton plan en 5 lignes ; attends mon accord avant le code. Termine par la commande pour tester.
```

### Commandes utiles
```bash
docker compose exec web python manage.py test reports        # tests d'une app
docker compose exec web python manage.py test                # tous les tests
docker compose logs -f web                                   # voir les erreurs
```

---

## Équipe 4 · `reports/checks.py`, `reports/tests.py`, `reports/models.py`

| Id | Tâche | Critère de fin | Taille |
| --- | --- | --- | --- |
| B-1 | `check_gps_accuracy` : refuser si précision > 50 m | un envoi à 80 m de précision renvoie 422 `GPS_INACCURATE` avec `accuracy_m` et `max_m` dans `details` | 10 min |
| B-2 | `check_zone` : téléphone hors Cotonou → `OUT_OF_ZONE` | un envoi à Ouidah (6.36, 2.08) est refusé ; un point au centre de Cotonou passe | 15 min |
| B-3 | `check_photo_file` : taille, format, fichier lisible | un `.txt` renommé en `.jpg` et un fichier de 9 Mo donnent 415 `PHOTO_INVALID`, une vraie photo passe | 25 min |
| B-4 | Un test par vérification (B-1 à B-3), sur le modèle de `test_too_far_is_rejected…` | `manage.py test reports` passe, chaque test échoue si on supprime la vérification | 20 min |
| B-5 | Charger le vrai polygone de Cotonou avec `load_zone` si un GeoJSON est fourni | `is_in_cotonou` utilise le polygone, un point en mer est refusé | 20 min |
| B-6 | Rejeter proprement une photo orientée par EXIF (lire l'orientation sans tourner le fichier d'origine) | une photo de téléphone prise en portrait est acceptée | 20 min (bonus) |

**Prompt B-1**
```text
Contexte : lis AGENTS.md, backend/AGENTS.md et docs/verification.md.
Tâche : implémente la vérification 3, check_gps_accuracy : si sub.device_accuracy_m dépasse settings.GPS_MAX_ACCURACY_M, lève Rejection("GPS_INACCURATE") avec details accuracy_m et max_m.
Modèle à suivre : check_distance dans reports/checks.py.
Fichiers : reports/checks.py et reports/tests.py. Ne modifie rien d'autre.
Critère de fin : un test envoie une précision de 80 m et reçoit 422 GPS_INACCURATE ; un test envoie 12 m et reçoit 201.
Contraintes : aucune dépendance ajoutée, seuil lu dans settings.
D'abord ton plan en 5 lignes ; attends mon accord. Termine par la commande pour tester.
```

**Prompt B-3**
```text
Contexte : lis AGENTS.md et docs/verification.md.
Tâche : implémente check_photo_file : fichier ≤ MAX_PHOTO_MB, format JPEG/PNG/WebP vérifié avec Pillow (Image.open puis verify), sinon Rejection("PHOTO_INVALID"). Remets le curseur du fichier au début après la lecture (sub.photo.seek(0)).
Modèle à suivre : check_distance.
Fichiers : reports/checks.py et reports/tests.py.
Critère de fin : trois tests : faux .jpg texte, fichier trop gros, vraie image. Les deux premiers donnent 415, le dernier passe.
Contraintes : aucune dépendance ajoutée. Dis-moi si tu n'es pas sûr d'une option de Pillow.
D'abord ton plan en 5 lignes.
```

---

## Équipe 5 · `verification/`

| Id | Tâche | Critère de fin | Taille |
| --- | --- | --- | --- |
| V-1 | `check_photo_not_reused` : empreinte déjà vue → `PHOTO_REUSED` | la même photo envoyée deux fois : 201 puis 422 | 10 min |
| V-2 | `check_duplicate` : trouver le signalement actif proche, même catégorie | deux envois à 20 m : le second renvoie 200 `duplicate: true` et `support_count: 2` | 25 min |
| V-3 | Tests du doublon : 20 m (fusion), 200 m (nouveau), autre catégorie (nouveau), ancien de 40 jours (nouveau) | 4 tests verts | 20 min |
| V-4 | `check_photo_content` avec le client simulé : lire le verdict, rejeter capture d'écran et hors sujet, enregistrer le verdict dans `sub.ai_verdict` | un fichier nommé `screenshot.jpg` donne 422 `PHOTO_SCREENSHOT` | 25 min |
| V-5 | Appliquer le seuil de confiance (`AI_MIN_CONFIDENCE`) et traiter `matches_category: false` → `PHOTO_MISMATCH` | un verdict simulé à 0,4 de confiance est refusé | 15 min |
| V-6 | `LiveVisionClient` : appel réel, JSON analysé strictement, délai `AI_TIMEOUT_S`, toute réponse mal formée = échec | un test avec une réponse invalide simulée ne publie rien | 30 min |
| V-7 | Décision « le modèle ne répond pas » : appliquer le choix validé (recommandation : garder en `pending`) | une panne simulée donne le comportement choisi, sans erreur 500 | 20 min |

**Prompt V-2**
```text
Contexte : lis AGENTS.md, backend/AGENTS.md, docs/verification.md et docs/data-model.md.
Tâche : implémente la vérification 8, check_duplicate. Cherche un Report de la même catégorie, au statut published ou in_progress, créé depuis moins de DUPLICATE_DAYS jours, à moins de DUPLICATE_RADIUS_M mètres du point (dwithin avec D(m=…) sur le champ location). Si trouvé, renseigne sub.duplicate_of ; ne lève rien et n'incrémente rien, services.py s'en charge.
Fichiers : verification/duplicates.py et verification/tests.py (à créer). Ne touche pas à models.py.
Critère de fin : test avec deux points à 20 m (doublon) et à 200 m (pas doublon).
Contraintes : aucune dépendance ajoutée, GeoJSON et Point = (longitude, latitude), vérifie l'ordre.
D'abord ton plan en 5 lignes.
```

**Prompt V-6**
```text
Contexte : lis AGENTS.md et docs/verification.md (section « Modèle de vision »).
Tâche : implémente LiveVisionClient.verify : envoie la photo et le prompt de docs/verification.md au modèle choisi par les mentors, avec un délai AI_TIMEOUT_S. La réponse doit être un JSON strict avec les 6 clés attendues ; toute réponse mal formée est un échec, jamais devinée.
Modèle à suivre : MockVisionClient dans verification/vision.py (même signature).
Fichiers : verification/vision.py uniquement.
Critère de fin : trois tests avec un faux transport : réponse valide, JSON invalide, délai dépassé.
Contraintes : la clé d'API vient de l'environnement, jamais du code ; ne journalise ni la photo ni la raison ; dis-moi si tu n'es pas sûr d'une API.
D'abord ton plan en 5 lignes.
```

---

## Équipe 6 · `whatsapp/`

| Id | Tâche | Critère de fin | Taille |
| --- | --- | --- | --- |
| W-1 | Reconnaître « Signaler » (minuscules, sans accents, espaces ignorés) | `normalize_text` appliqué, 4 variantes reconnues par un test | 10 min |
| W-2 | `handle_incoming` : créer la `CaptureSession` WhatsApp et répondre avec le lien | le `curl` de `docs/whatsapp.md` écrit un lien `/capture/<token>` dans les logs | 25 min |
| W-3 | Message d'aide pour tout autre texte | un message « bonjour » reçoit l'aide, pas de lien | 10 min |
| W-4 | Ignorer sans erreur les événements non texte (statuts, images) | un statut de livraison renvoie 200 sans réponse envoyée | 10 min |
| W-5 | Confirmation avec le code de suivi après un signalement réussi (canal WhatsApp) | un envoi avec ce lien produit un message « CS-XXXXXX » dans les logs | 25 min |
| W-6 | `send_text` en mode `live` (API WhatsApp Business) | un message de test arrive sur le numéro de la sandbox | 30 min |
| W-7 | Tunnel HTTPS public et vérification du webhook côté Meta | la vérification Meta passe (`hub.challenge`) | 20 min, avec un mentor |

**Prompt W-2**
```text
Contexte : lis AGENTS.md, backend/AGENTS.md et docs/whatsapp.md.
Tâche : implémente handle_incoming(payload) : pour chaque message texte (iter_text_messages) dont le texte normalisé vaut « signaler », crée CaptureSession.create_for("whatsapp", …) avec reporter_ref (jamais le numéro), puis envoie le lien capture_url avec client.send_text.
Modèle à suivre : les tests de whatsapp/tests.py.
Fichiers : whatsapp/handlers.py et whatsapp/tests.py. Ne modifie ni views.py ni signature.py.
Critère de fin : le curl de docs/whatsapp.md fait apparaître un lien dans les logs de web ; test : le numéro n'apparaît nulle part en clair.
Contraintes : aucune dépendance ajoutée, répondre 200 vite, ne jamais journaliser un numéro en clair (mask_number).
D'abord ton plan en 5 lignes.
```

---

## Tâches transverses (mentors, à répartir)

| Id | Tâche | Qui | Critère de fin |
| --- | --- | --- | --- |
| M-1 | Valider les seuils (50 m, 100 m, 30 m, 0,6) avec les organisateurs | Jean | valeurs figées dans `.env.example` |
| M-2 | Décider le comportement si le modèle de vision ne répond pas | Jean | choix écrit dans `docs/verification.md` |
| M-3 | Geler le contrat à 20h20 : relire `/api/docs/` avec Noé | Jean + Noé | plus aucun renommage |
| M-4 | Répéter la démonstration de bout en bout (web puis WhatsApp) | tous | scénario de 3 minutes sans accroc |
| M-5 | Données de démonstration : vérifier `seed_demo`, aucune donnée réelle | Jean | 8 signalements « [démo] » visibles |

---

## Bonus (P2), pour ceux qui finissent tôt
| Id | Tâche | Fichiers | Critère de fin |
| --- | --- | --- | --- |
| P-1 | `POST /reports/{code}/support` : « +1 » depuis la carte, position vérifiée | `reports/views.py`, `urls.py` | le compteur augmente, un second +1 depuis la même source est refusé |
| P-2 | `GET /agent/stats` : comptages par statut et catégorie | `reports/views.py` | JSON limité aux catégories de l'agent |
| P-3 | Enregistrer les rejets (statut `rejected`, code, sans donnée personnelle) | équipe 4 | un rejet apparaît dans l'admin |
| P-4 | Floutage des visages et plaques | équipe 5 | photo publique floutée, originale conservée |
| P-5 | Journal d'audit des changements de statut | équipe 4 | chaque PATCH agent laisse une trace |

Règle d'or : si une tâche demande de **changer le contrat ou un modèle**, on s'arrête et on demande à l'équipe 4 et à un mentor.

## Pour Noé : tâches front qui dépendent du back
| Id | Tâche | Dépend de |
| --- | --- | --- |
| F-1 | Page de capture : `GET /capture-sessions/{token}`, caméra, GPS, envoi `POST /reports` | B-1 à B-3 pour les refus |
| F-2 | Afficher les 422 : lire `error.code` et `message`, proposer de corriger puis réessayer | `docs/api-contract.md` |
| F-3 | Carte : `GET /reports` en GeoJSON, `[longitude, latitude]` | déjà disponible |
| F-4 | Suivi : `GET /reports/{code}` | déjà disponible |
| F-5 | Espace mairie : login, liste, `PATCH`, photo « après » | agents de démonstration |

## Ordre conseillé pour ne pas se bloquer
1. **Tout de suite** (rien ne dépend de rien) : B-1, B-2, V-1, V-2, W-1, W-2, F-3.
2. **Ensuite** : B-3, V-4, W-3, W-4, F-1, F-2.
3. **Puis** : tests (B-4, V-3), V-5, W-5, F-4, F-5.
4. **Si le temps le permet** : V-6, W-6, W-7, bonus P.
