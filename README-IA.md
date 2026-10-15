# Règles IA du projet · mode d'emploi

## Principe
Une seule source de vérité : `AGENTS.md`. Son nom est neutre et lu par un nombre croissant d'outils (dont plusieurs open source). Tous les autres fichiers de ce dossier sont de petits pointeurs vers lui, pour les outils qui cherchent un autre nom. On ne modifie les règles qu'à un seul endroit.

## Quel fichier pour quel outil
| Outil | Fichier lu | Remarque |
| --- | --- | --- |
| Outils qui suivent le format `AGENTS.md` (par exemple OpenCode, Codex, Cursor, Copilot) | `AGENTS.md` | Rien d'autre à faire |
| Claude Code | `CLAUDE.md` | Importe `AGENTS.md` avec `@AGENTS.md` |
| Gemini CLI | `GEMINI.md` | Pointeur ; le nom du fichier de contexte est aussi réglable dans ses paramètres |
| Cursor | `.cursor/rules/cotonou-signale.mdc` | Règle toujours active qui renvoie vers `AGENTS.md` |
| GitHub Copilot | `.github/copilot-instructions.md` | Pointeur |
| Aider | `CONVENTIONS.md` + `.aider.conf.yml` | Le fichier de configuration charge `AGENTS.md` en lecture seule |
| Cline et dérivés | `.clinerules` | Pointeur |

Les noms de fichiers évoluent vite : si un outil ne semble pas lire les règles, ouvrir sa documentation et vérifier le nom attendu avant de dupliquer du contenu. Dernier recours : coller le contenu de `AGENTS.md` au début de la conversation.

## Où mettre ces fichiers
À la racine du dépôt, en conservant les dossiers `backend/` et `frontend/`. Attention : `.cursor/`, `.github/`, `.aider.conf.yml` et `.clinerules` commencent par un point, ils sont cachés dans l'explorateur de fichiers.

## À adapter avant la soirée
- Les numéros d'équipe et leurs zones (tableau en bas de `AGENTS.md`), une fois les 6 équipes formées.
- Les noms de services Docker (`web`, `web-front`) dans les commandes, selon le `docker-compose.yml` réel.
- Les seuils (50 m, 100 m, 30 m, 0,6) s'ils changent : les modifier d'abord dans `AGENTS.md`.
- La phrase sur le gel du contrat (20h20) si l'horaire bouge.

## Bon réflexe
Au début de la soirée, demander à chaque équipe de lancer son outil sur le dépôt et de poser la question « Quelles sont les règles du projet ? ». Si l'outil répond avec le contenu de `AGENTS.md`, la configuration est bonne.
