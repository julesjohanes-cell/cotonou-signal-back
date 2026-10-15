# Parcours WhatsApp

WhatsApp est la deuxième porte d'entrée. La vérification est exactement la même que sur le web : le citoyen ouvre une page de capture via un lien unique, et le serveur vérifie GPS et photo.

## Déroulé
1. Le citoyen écrit « Signaler » au numéro de la plateforme.
2. Meta appelle `POST /api/v1/webhooks/whatsapp`. Le serveur vérifie la signature `X-Hub-Signature-256` (HMAC-SHA256 du corps brut avec le secret de l'application, comparaison avec `hmac.compare_digest`), puis répond `200` immédiatement.
3. Le serveur compare le texte normalisé (minuscules, sans accents) à « signaler », crée une `CaptureSession` de 10 min avec `reporter_ref` (HMAC du numéro) et envoie un message contenant `<FRONT_URL>/capture/<token>`.
4. Le citoyen ouvre le lien : la page appelle `GET /capture-sessions/{token}`, puis suit le même parcours que sur le web, vers `POST /reports`.
5. Après vérification, le serveur envoie la confirmation et le code de suivi dans la même discussion.

## Configuration du webhook
- `GET /api/v1/webhooks/whatsapp` : Meta envoie `hub.mode`, `hub.verify_token` et `hub.challenge`. Si le jeton est correct, répondre avec le `hub.challenge` en texte brut.
- Il faut une URL HTTPS publique : tunnel de type ngrok ou Cloudflare Tunnel en local.
- Le numéro de test de la sandbox Meta suffit pour la démonstration si le compte de production n'est pas validé.
- Le citoyen écrit en premier : les réponses libres sont normalement possibles dans la fenêtre de 24 h qui suit son message, ce qui évite d'attendre l'approbation de modèles de messages. À confirmer dans la documentation Meta de la version utilisée.

## Variables d'environnement
| Variable | Rôle |
| --- | --- |
| `WHATSAPP_MODE` | `mock` (messages sortants écrits dans les logs) ou `live` |
| `WHATSAPP_VERIFY_TOKEN` | Jeton choisi par nous, renvoyé lors de la vérification du webhook |
| `WHATSAPP_APP_SECRET` | Secret de l'application Meta, pour la signature des requêtes |
| `WHATSAPP_ACCESS_TOKEN` | Jeton pour envoyer des messages |
| `WHATSAPP_PHONE_NUMBER_ID` | Identifiant du numéro d'envoi |
| `FRONT_URL` | Base des liens de capture envoyés aux citoyens |
| `REPORTER_HMAC_KEY` | Clé de calcul de `reporter_ref` |

Aucune de ces valeurs n'est commitée : tout passe par `.env`, avec un `.env.example` sans valeurs réelles.

## État actuel du code
Déjà en place : vérification du webhook (`GET`), contrôle de la signature `X-Hub-Signature-256`, extraction des messages texte (`iter_text_messages`), client d'envoi simulé (`WHATSAPP_MODE=mock`), masquage des numéros dans les logs, calcul de l'identifiant anonyme (`reporter_ref`). À faire par l'équipe 6 : `handle_incoming` (voir `docs/tasks.md`).

La signature est exigée dès que `WHATSAPP_APP_SECRET` est renseigné **ou** que `WHATSAPP_MODE` n'est plus `mock`. En `mock` sans secret, on peut tester avec un simple `curl`, sans signer :
```bash
curl -X POST localhost:8000/api/v1/webhooks/whatsapp -H 'Content-Type: application/json' \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"22990000000","type":"text","text":{"body":"Signaler"}}]}}]}]}'
```

## Règles
- Ne jamais journaliser ni stocker un numéro de téléphone en clair : seulement `reporter_ref`.
- Traiter vite et répondre `200` : tout le reste se fait après.
- Ignorer sans erreur les événements qui ne sont pas des messages texte entrants (statuts de livraison, etc.).
