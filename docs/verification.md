# Vérification d'un signalement

Chaque signalement, web ou WhatsApp, passe par la même suite de vérifications dans `POST /reports`, du moins coûteux au plus coûteux.

## Où est le code
Chaque vérification est une fonction `check_xxx(sub)` dans son fichier, listée dans l'ordre dans `verification/pipeline.py`. Elle ne renvoie rien et lève `Rejection("CODE", message, details)` si elle refuse. Les vérifications 1 à 5 sont dans `reports/checks.py` (équipe 4), les vérifications 6 à 8 dans `verification/` (équipe 5). Les n° 1 et 5 sont écrites ; les autres sont à faire (`docs/tasks.md`).

## Ordre des vérifications
1. Jeton de capture valide, non expiré, non utilisé (`TOKEN_EXPIRED`, `TOKEN_USED`).
2. Photo lisible, JPEG, PNG ou WebP, 8 Mo maximum (`PHOTO_INVALID`).
3. Précision GPS du téléphone inférieure ou égale à 50 m (`GPS_INACCURATE`).
4. Position du téléphone dans le polygone de Cotonou (`OUT_OF_ZONE`).
5. Distance entre le point et le téléphone inférieure ou égale à 100 m (`TOO_FAR`).
6. Empreinte SHA-256 de la photo jamais vue : une photo réutilisée est refusée (`PHOTO_REUSED`).
7. Vérification par le modèle de vision : la photo montre la catégorie déclarée et n'est pas une capture d'écran (`PHOTO_MISMATCH`, `PHOTO_SCREENSHOT`).
8. Doublon : même catégorie, moins de 30 m, signalement actif sur les 30 derniers jours. Si oui, on fusionne et on incrémente `support_count`.

Si tout passe, le statut devient `published`, sauf pour `autre` qui devient `moderation`.

## Seuils (valeurs de départ, à valider par l'équipe)
| Seuil | Valeur | Réglage |
| --- | --- | --- |
| Précision GPS maximale | 50 m | un seul fichier de réglages |
| Distance point / téléphone | 100 m (fixée par le concept) | idem |
| Rayon de doublon | 30 m | idem |
| Ancienneté d'un doublon | 30 jours | idem |
| Confiance minimale du modèle de vision | 0,6 | idem |
| Durée de validité d'un lien de capture | 10 min | idem |
| Taille maximale de la photo | 8 Mo | idem |
| Délai maximal du modèle de vision | 15 s | idem |

## Ce que garantit « photo prise sur place »
Le serveur ne peut pas prouver qu'une photo vient de l'appareil photo. Les protections réelles sont :
- la capture se fait dans la page de capture, avec la caméra du navigateur ;
- le lien est à usage unique et expire en 10 min ;
- l'empreinte SHA-256 bloque la réutilisation d'une photo ;
- le modèle de vision rejette les captures d'écran et les photos d'écran.

À dire : « pris en direct et vérifié ». À ne pas dire : « infalsifiable ».

## Modèle de vision
Le back est le seul à appeler le modèle. Réglage `VERIFY_MODE=mock|live` : en `mock`, le verdict est prévisible (accepte tout sauf un fichier nommé `screenshot`), pour que le front et la démonstration ne dépendent jamais d'une clé ou d'un quota.

Prompt de départ :
```text
Tu vérifies un signalement citoyen d'insalubrité à Cotonou.
Catégorie déclarée : {label}.
Réponds uniquement par un objet JSON, sans autre texte :
{
  "matches_category": true ou false,
  "is_screenshot_or_screen_photo": true ou false,
  "is_public_outdoor_space": true ou false,
  "contains_identifiable_person": true ou false,
  "confidence": nombre entre 0 et 1,
  "reason": "une phrase en français"
}
Si l'image est une capture d'écran, une photo d'un écran, un dessin ou n'a aucun rapport
avec la catégorie, matches_category vaut false.
```

Règles de code :
- analyser le JSON strictement ; toute réponse mal formée est un échec, jamais devinée ;
- ne jamais exposer `reason` ni le verdict au public ;
- fixer un délai maximal (15 s) ;
- enregistrer le verdict dans `Report.ai_verdict`.

## Décision ouverte
Que faire si le modèle de vision dépasse le délai : rejeter, ou garder le signalement en `pending`, visible des agents seulement ? Recommandation : garder en `pending`. À confirmer par l'équipe avant la démonstration.

## Journalisation
Journaliser chaque rejet avec son code (sans donnée personnelle) : utile pour déboguer en direct et pour montrer la valeur de la vérification.
