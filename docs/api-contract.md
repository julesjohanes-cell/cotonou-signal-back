# Contrat d'API v0 (version lisible)

La source de vérité technique est `docs/openapi.yaml`, généré par le code (drf-spectacular). En cas de désaccord entre ce document et lui, c'est le fichier OpenAPI qui gagne. Ce document sert à comprendre l'intention et à démarrer vite.

Le contrat est gelé à 20h20 le jeudi 15 octobre : après, on ajoute (champ facultatif, nouvel endpoint), on ne renomme ni ne supprime rien.

## Règles communes
- Préfixe `/api/v1`, JSON partout, sauf l'envoi de photos en `multipart/form-data`.
- Noms de champs en `snake_case`, dates en ISO 8601 UTC (`2026-10-15T19:42:10Z`).
- **GeoJSON impose `[longitude, latitude]`.** Dans les formulaires, chaque coordonnée est nommée (`point_lat`, `point_lng`, …), jamais un tableau.
- Toute erreur a la même forme : `{"error": {"code": "TOO_FAR", "message": "…", "details": {}}}`. Le front affiche `message` (en français) et se base sur `code`.
- CORS autorisé pour l'URL du front uniquement. Les agents s'authentifient par `Authorization: Token <jeton>`.

## Endpoints
| Méthode et chemin | Rôle | Accès | Priorité |
| --- | --- | --- | --- |
| `GET /categories` | Les 8 catégories et le routage vers les services | Public | P0 |
| `POST /reports` | Créer un signalement : photo, position, catégorie. Vérifie, puis publie ou rejette | Public (jeton de capture) | P0 |
| `GET /reports` | Signalements publiés au format GeoJSON, filtres `status`, `category`, `bbox` | Public | P0 |
| `GET /reports/{tracking_code}` | Détail et historique d'un signalement, pour le suivi citoyen | Public | P0 |
| `POST /auth/login` | Connexion d'un agent, renvoie un jeton | Agent | P0 |
| `GET /agent/reports` | Signalements du service de l'agent, avec verdict IA | Agent | P0 |
| `PATCH /agent/reports/{tracking_code}` | Changer le statut avec une note (transitions contrôlées) | Agent | P0 |
| `POST /capture-sessions` | Créer un lien de capture à usage unique, valable 10 min (parcours web) | Public, limité en débit | P1 |
| `GET /capture-sessions/{token}` | Vérifier qu'un lien est valide avant d'ouvrir la page de capture | Public | P1 |
| `GET /webhooks/whatsapp` | Vérification du webhook par Meta (renvoie le `hub.challenge`) | Meta | P1 |
| `POST /webhooks/whatsapp` | Réception des messages : « Signaler » crée un lien et répond au citoyen | Meta (signature) | P1 |
| `POST /agent/reports/{tracking_code}/after-photo` | Ajouter la photo « après » et passer en `resolved` | Agent | P1 |
| `POST /reports/{tracking_code}/support` | Ajouter un « +1 » depuis la carte | Public (position vérifiée) | P2 |
| `GET /agent/stats` | Comptages par statut, catégorie et délai de traitement | Agent | P2 |
| `GET /health` | Vérifie que l'API, la base et PostGIS répondent | Public | P0 |

Pendant le développement, l'exigence du jeton de capture sur `POST /reports` peut être désactivée par réglage (`REQUIRE_CAPTURE_TOKEN=false`), puis activée.

## `POST /reports`
Champs du formulaire : `category` (slug), `description` (facultatif, 280 caractères), `photo` (fichier), `point_lat` et `point_lng` (le point du problème, ajusté sur la carte), `device_lat`, `device_lng`, `device_accuracy_m` (la position du téléphone), `capture_token`.

```bash
curl -X POST $API/api/v1/reports \
  -F category=depot_sauvage \
  -F description="Depotoir devant un etal" \
  -F point_lat=6.3703 -F point_lng=2.3912 \
  -F device_lat=6.3704 -F device_lng=2.3911 -F device_accuracy_m=12 \
  -F capture_token=$TOKEN \
  -F photo=@photo.jpg
```

Réponse `201` (publié) :
```json
{
  "tracking_code": "CS-7K3F9Q",
  "status": "published",
  "duplicate": false,
  "support_count": 1,
  "message": "Signalement publié. Suivez-le avec ce code."
}
```

Réponse `200` (doublon fusionné) : même forme, avec `"duplicate": true`, le `tracking_code` du signalement existant et son `support_count` incrémenté.

Réponse `422` (rejet) :
```json
{
  "error": {
    "code": "TOO_FAR",
    "message": "Le point est à plus de 100 m de votre position.",
    "details": { "distance_m": 142 }
  }
}
```

## `GET /reports` (carte)
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": { "type": "Point", "coordinates": [2.3912, 6.3703] },
    "properties": {
      "tracking_code": "CS-7K3F9Q",
      "category": "depot_sauvage",
      "status": "published",
      "support_count": 3,
      "photo_url": "/media/reports/2026/10/abc.jpg",
      "created_at": "2026-10-15T19:42:10Z"
    }
  }]
}
```
Le GeoJSON public ne contient jamais `reporter_location`, `reporter_ref`, `ai_verdict` ni `distance_m`.

## Codes d'erreur
| Code | HTTP | Quand |
| --- | --- | --- |
| `INVALID_INPUT` | 400 | Champ manquant ou mal formé (`details` liste les champs) |
| `PHOTO_INVALID` | 415 | Fichier illisible ou type non accepté |
| `UNAUTHENTICATED` / `FORBIDDEN` | 401 / 403 | Agent non connecté ou hors de son service |
| `NOT_FOUND` | 404 | Code de suivi inconnu |
| `TOKEN_USED` | 409 | Lien de capture déjà utilisé |
| `INVALID_TRANSITION` | 409 | Changement de statut interdit |
| `TOKEN_EXPIRED` | 410 | Lien de capture expiré |
| `OUT_OF_ZONE`, `TOO_FAR`, `GPS_INACCURATE`, `PHOTO_REUSED`, `PHOTO_MISMATCH`, `PHOTO_SCREENSHOT` | 422 | Rejet par une vérification (voir `docs/verification.md`) |
| `RATE_LIMITED` | 429 | Trop de requêtes pour ce jeton ou cette adresse IP |

## Précisions issues de l'implémentation
- **Barre oblique finale** : `/reports` et `/reports/` sont acceptés tous les deux.
- **Un rejet n'est pas enregistré** et ne consomme pas le lien de capture : le citoyen peut corriger (par exemple rapprocher le point) et réessayer avec le même lien. Seul un envoi réussi, y compris un doublon fusionné, consomme le lien.
- **`POST /auth/login`** : corps JSON `{"username", "password"}` ; réponse `{"token", "user": {"username", "services": [...]}}`. Ensuite : `Authorization: Token <token>`.
- **`GET /agent/reports`** : réponse `{"count": 12, "results": [...]}`, paramètres `status`, `limit` (100 par défaut, 500 max), `offset`. Chaque résultat contient le détail du signalement plus `channel` et `ai_verdict`. Un agent ne voit que les catégories de ses services ; l'administrateur voit tout.
- **`PATCH /agent/reports/{code}`** : corps JSON `{"status": "in_progress" | "resolved", "note": "…"}`. Transitions : `published → in_progress → resolved`. Une catégorie sans service (« Autre problème ») n'est visible que de l'administrateur, qui la traite dans l'admin Django.
- **`POST /agent/reports/{code}/after-photo`** : `multipart/form-data` avec `photo` et `note` ; autorisé depuis `in_progress` (passe en `resolved`) ou depuis `resolved` si la photo « après » manque encore.
- **`GET /reports/{code}`** : champs `tracking_code, category, category_label, status, description, lat, lng, photo_url, photo_after_url, support_count, created_at, updated_at, resolved_at, history[]`. L'historique ne contient pas le nom de l'agent, mais sa note est visible du citoyen.
- **`POST /capture-sessions`** : réponse `201 {"token", "expires_at", "capture_url"}`. **`GET /capture-sessions/{token}`** : `200 {"valid": true, "expires_at"}`, ou `404 / 409 TOKEN_USED / 410 TOKEN_EXPIRED`.
- **`GET /reports`** : au plus 2000 résultats ; `bbox` = `min_lng,min_lat,max_lng,max_lat`.
- **Limitation de débit** : 60 requêtes/min sur `POST /reports`, 30/min sur `POST /capture-sessions`, 10/min sur la connexion, par adresse IP (réglable dans `.env`).
- **Non implémentés (P2)** : `POST /reports/{code}/support` et `GET /agent/stats`.

## Changer le contrat
1. Proposer la modification (champ, endpoint, code) à voix haute et dans une demande de fusion.
2. Mettre à jour `docs/openapi.yaml` et, si nécessaire, ce document.
3. Prévenir les équipes front concernées. Après le gel, uniquement des ajouts.
