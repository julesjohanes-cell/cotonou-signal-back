# Front-end · Next.js (règles pour les assistants IA)

Complète le `AGENTS.md` de la racine, qui reste prioritaire. Contrat : `docs/openapi.yaml`.

## Structure
- Équipe 1 : parcours de capture (catégorie, caméra, GPS, point sur la carte, envoi).
- Équipe 2 : carte des signalements, détail, suivi par code.
- Équipe 3 : espace mairie (connexion, liste, changement de statut, photo « après »).

## Commandes
```bash
docker compose up            # lance aussi le front
docker compose exec web-front npm run dev
docker compose exec web-front npm run lint
```
L'URL de l'API vient de `NEXT_PUBLIC_API_URL`. En attendant le vrai back, pointer vers le serveur factice (Prism) lancé à partir de `docs/openapi.yaml`.

## Règles
- TypeScript strict. Générer les types depuis le contrat (`openapi-typescript`) plutôt que de les écrire à la main ; un seul client d'API partagé.
- Ne jamais appeler un champ ou un endpoint absent du contrat. Gérer chaque code d'erreur du contrat avec un message en français tiré du champ `message` de la réponse.
- Mobile d'abord : écrans pensés pour un téléphone et une connexion lente.
- Pas de nouvelle dépendance sans accord d'un mentor.

## Capture citoyen
- Photo : caméra uniquement (`<input type="file" accept="image/*" capture="environment">` ou `getUserMedia`), pas de choix depuis la galerie.
- Position : `navigator.geolocation` avec `enableHighAccuracy: true` ; envoyer `device_lat`, `device_lng` et `device_accuracy_m`. Si la précision dépasse 50 m, demander à l'utilisateur d'attendre ou de se déplacer avant d'envoyer.
- Le point du problème (`point_lat`, `point_lng`) est ajustable sur la carte mais ne peut pas s'éloigner de plus de 100 m de la position du téléphone : afficher ce rayon et empêcher le dépassement.
- Réduire la photo avant envoi (par exemple 1600 px de large, qualité 0,8) pour économiser les données mobiles.
- Le lien de capture contient un jeton (`/capture/<token>`) : l'appeler via `GET /capture-sessions/{token}` avant d'afficher la page, et traiter `TOKEN_EXPIRED` et `TOKEN_USED`.

## Carte
- MapLibre + OpenStreetMap. Les coordonnées GeoJSON sont `[longitude, latitude]`.
- N'afficher que ce que renvoie l'API publique. Jamais de position de citoyen.
- Après un envoi réussi, afficher le `tracking_code` de façon visible et copiable.

## Vie privée
- Aucune donnée personnelle réelle dans les données de démonstration ni dans les captures d'écran du projet.
- Aucun secret dans le code ou dans les variables `NEXT_PUBLIC_*`.
