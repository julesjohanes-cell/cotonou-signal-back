# Travailler en équipe avec l'IA

La règle d'or : **l'IA écrit, l'humain décide et vérifie, le contrat d'API juge.** Le chaos vient presque toujours de trois sources : chacun donne à l'IA un contexte différent, l'IA modifie des fichiers qu'elle ne devrait pas toucher, et personne ne vérifie en exécutant.

## 1. Un contexte partagé
Les règles sont dans `AGENTS.md` (racine, `backend/`, `frontend/`). Chaque équipe lance son outil d'IA sur le dépôt et vérifie qu'il connaît ces règles (voir `README-IA.md`). Une règle à changer se change dans `AGENTS.md`, nulle part ailleurs.

## 2. Un propriétaire par zone
| Équipe | Zone | Mentor |
| --- | --- | --- |
| 1 · Capture citoyen | Page de capture : catégorie, caméra, GPS, point sur la carte, appel à `POST /reports` | Noé |
| 2 · Carte et suivi | Carte des signalements, détail, suivi par code | Noé |
| 3 · Espace mairie | Connexion agent, liste, changement de statut, photo « après » | Noé |
| 4 · Cœur du back | Modèles, `POST /reports`, vérifications GPS, GeoJSON | Jean |
| 5 · Intégrité | Vérification par le modèle de vision, empreinte, doublons « +1 » | Jean |
| 6 · WhatsApp | Webhook, sessions de capture, messages de confirmation | Jean |

Ce découpage est une proposition, à confirmer une fois les équipes formées. Seule l'équipe 4 modifie `models.py` et crée des migrations : les autres lui demandent un champ plutôt que de l'ajouter. C'est la cause numéro un de blocage sous Django.

## 3. La boucle de travail de 20 minutes
1. **Lire** la partie du contrat concernée.
2. **Écrire le prompt de tâche** : contexte, extrait du contrat, fichiers à toucher, critères d'acceptation.
3. **Demander un plan d'abord** (5 lignes). Un débutant valide le plan avant de voir du code.
4. **Générer petit** : un endpoint ou une fonction, pas « tout le module ».
5. **Exécuter** : `curl`, la page `/api/docs/` ou un test. Lire du code ne prouve rien, l'exécuter oui.
6. **Relire avec trois questions** : respecte-t-il le contrat ? Ai-je vu qu'il marche ? Puis-je l'expliquer en une phrase ?
7. **Commit petit**, message clair, fusion rapide dans `main`.

### Modèle de prompt de tâche
```text
Contexte : lis AGENTS.md, backend/AGENTS.md et docs/openapi.yaml.
Tâche : implémente la vérification 3 (check_gps_accuracy) sur le modèle de check_distance.
Fichiers : reports/checks.py (et son test dans reports/tests.py).
Critères : 422 avec le code GPS_INACCURATE si la précision dépasse le seuil, sans changer le comportement des autres cas ; un test.
Contraintes : pas de nouvelle dépendance, ne touche pas à models.py.
Donne d'abord ton plan en 5 lignes, attends mon accord, puis le code et la commande de test.
```

## 4. Dix règles anti-chaos
1. **Le contrat gèle à 20h20.** Après, on ajoute (champ facultatif, nouvel endpoint), on ne renomme ni ne supprime rien. Tout changement est annoncé à voix haute et passe par `openapi.yaml`.
2. **`main` démarre toujours** avec `docker compose up`. Si elle casse, on corrige avant tout le reste.
3. **Branches courtes**, un commit toutes les 20 minutes, fusion à chaque tâche terminée.
4. **Une zone, une équipe.** L'IA ne sort pas du périmètre donné dans le prompt.
5. **Aucune dépendance ajoutée** sans l'accord d'un mentor : l'IA en ajoute volontiers et casse l'installation des autres.
6. **Aucun secret dans le code ni dans un prompt.** Clés dans `.env`, jamais de vraies données personnelles collées dans l'IA.
7. **Diff minimal** : on interdit à l'IA de « nettoyer » ou de réécrire un fichier entier.
8. **Règle des deux essais :** si l'IA échoue deux fois sur le même problème, on s'arrête, on lui donne l'erreur exacte et le fichier concerné, ou on appelle un mentor. Pas de troisième essai à l'aveugle.
9. **Vérifier ce qui semble inventé** : une bibliothèque, une option ou une URL suggérée par l'IA doit être testée (`import`, exécution) avant d'être gardée.
10. **On ne garde que ce qu'on comprend.** « Explique-moi ce code ligne par ligne » est un prompt légitime et encouragé.

## 5. Adapter le rôle au niveau de chacun
| Profil | Rôle conseillé | Ce que l'IA lui apporte |
| --- | --- | --- |
| Jamais codé | Pilote : écrit les prompts, teste dans `/api/docs/` et sur téléphone, prépare les données de démonstration et les cas de test | Un pair qui explique et écrit le code, pendant qu'il apprend à relire et à vérifier |
| Débutant | Prend une tâche simple et bien bornée (un écran, un serializer, un test) | Du code guidé, avec des explications à la demande |
| Junior | Responsable d'une tâche de bout en bout, avec tests | Un accélérateur, mais il doit réviser ce que l'IA produit |

Dans chaque équipe, une personne tape les prompts et une autre relit et exécute, puis on échange toutes les 20 minutes. Cela évite que le débutant subisse le code et que le junior le valide sans le lire.

## 6. Où l'IA aide, où rester vigilant
- **Où elle excelle :** données de démonstration (fixtures), tests, serializers, messages d'erreur en français, documentation.
- **Où il faut rester vigilant :** sécurité (signature du webhook, permissions), calculs géographiques (ordre longitude/latitude), migrations de base de données.

## 7. Repères de la soirée
| Horaire | Repère |
| --- | --- |
| 20h20 | Gel du contrat d'API |
| 20h20 – 21h20 | Développement, partie 1 |
| 21h20 – 21h35 | Pause : fusion dans `main`, vérification que tout démarre, premier signalement de bout en bout |
| 21h35 – 22h15 | Intégration du front sur le vrai back, une chose à la fois |
| 22h15 | Gel du code et répétition de la démonstration |
| 22h35 – 23h00 | Démonstration en direct : un vrai signalement, vu par la mairie |

Plan B de la démonstration : une courte vidéo du parcours complet et des signalements préchargés (`seed_demo`), au cas où le réseau ou WhatsApp tombent.
