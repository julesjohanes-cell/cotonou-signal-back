# Périmètre et priorités

Avec environ 2 h de développement et 6 équipes de niveaux variés, on vise un seul chemin de démonstration : signaler, vérifier, afficher sur la carte, changer le statut côté mairie.

## Principes
1. **Tranche verticale d'abord.** Un signalement de bout en bout, même naïf, avant d'ajouter la moindre vérification.
2. **Tout ce qui est externe est simulable.** Le modèle de vision et WhatsApp passent par une interface avec un mode `mock` : personne n'est bloqué par une clé API ou un compte non validé.
3. **Le contrat d'abord, le code ensuite.** `docs/openapi.yaml` est la seule source de vérité entre front, back et IA.

## Priorités du back
| Priorité | Contenu | Pourquoi |
| --- | --- | --- |
| P0 · démo | Catégories préchargées, création d'un signalement (photo + GPS + catégorie), liste GeoJSON pour la carte, suivi par code, connexion et changement de statut par un agent | C'est exactement la démonstration de clôture |
| P1 · fort impact | Vérification GPS stricte (Cotonou, 100 m), vérification photo par IA, doublons « +1 », parcours WhatsApp à lien unique, photo « après » | Ce qui rend Cotonou Signale différent des solutions voisines |
| P2 · si le temps | Hash SHA-256 de la photo, journal d'audit, floutage des visages et plaques, « Autre problème » en modération, statistiques mairie, « +1 » depuis la carte | Confiance de la mairie ; à présenter comme « prévu » si non codé |

## Critères de réussite à la clôture
- Un signalement complet en moins d'une minute.
- Une photo hors sujet refusée en direct.
- Le parcours WhatsApp à lien unique fonctionne.
- La mairie voit le point, change son statut, ajoute la photo après.
- Aucune donnée personnelle visible publiquement.

## Hors périmètre ce soir
Application native, mode hors ligne complet, capteurs IoT, connexion aux outils de la mairie.

## Au-delà de la soirée : ce qui donnera confiance à la mairie
| Axe | Contenu |
| --- | --- |
| Des données fiables | Position et photo vérifiées, doublons regroupés en « +1 » |
| La vie privée respectée | Visages et plaques floutés, position du citoyen jamais publique, cadre de l'APDP |
| Tout est tracé | Journal d'audit des actions, empreinte de chaque photo pour prouver qu'elle n'a pas été modifiée |
| Les données restent au Bénin | Hébergement possible localement, accès par rôle pour les agents |

## Règle de communication
Dans la démonstration et devant la mairie, ne présenter comme fait que ce qui est codé. Floutage, journal d'audit et hébergement local sont « prévus » tant qu'ils ne sont pas livrés.
