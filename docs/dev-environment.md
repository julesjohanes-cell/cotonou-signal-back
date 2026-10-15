# Environnement de développement

## Réponse courte : non, pas de `down` puis `up` à chaque modification
Le dossier `backend/` est **monté** dans le conteneur et Django tourne avec son serveur de développement
(`runserver`). Dès que vous enregistrez un fichier Python, le serveur se recharge tout seul en 1 à 2 secondes. On lance
`docker compose up` **une fois**, on laisse le terminal ouvert, et on code.

Vous savez que le rechargement a eu lieu quand le terminal affiche `… changed, reloading.` puis `Watching for file changes`.

## Que faire selon ce que vous modifiez
| Vous modifiez | Ce qu'il faut faire |
| --- | --- |
| Du code Python : vues, serializers, vérifications, `settings.py`, tests… | **Rien.** Rechargement automatique. |
| `reports/models.py` (équipe 4 uniquement) | `docker compose exec web python manage.py makemigrations` puis `docker compose exec web python manage.py migrate` |
| Les catégories (`reports/fixtures/categories.json`) | `docker compose exec web python manage.py loaddata categories` |
| `.env` | `docker compose up -d` : recrée le conteneur avec les nouvelles valeurs (rapide, **sans** reconstruire l'image) |
| `docker-compose.yml` | `docker compose up -d` |
| `requirements.txt`, `Dockerfile` ou `entrypoint.sh` (nouvelle bibliothèque) | `docker compose up --build` : reconstruit l'image. **Demandez d'abord l'accord d'un mentor** pour toute nouvelle dépendance. |
| La base est dans un état cassé | `docker compose down -v` puis `docker compose up` : **efface la base ET les photos**, repart de zéro avec les données de démonstration |

Les **migrations** sont appliquées automatiquement à chaque démarrage (`entrypoint.sh`), donc après un `git pull` qui contient
une nouvelle migration, un simple redémarrage suffit : `docker compose restart web`.

## Les commandes du quotidien
```bash
docker compose up                 # démarre tout et affiche les logs (Ctrl+C pour arrêter)
docker compose up -d              # démarre en arrière-plan
docker compose logs -f web        # suivre les logs de l'API
docker compose stop               # arrête sans rien supprimer
docker compose start              # redémarre ce qui était arrêté
docker compose restart web        # relance seulement l'API (rarement utile)
docker compose down               # supprime les conteneurs, GARDE la base et les photos
docker compose down -v            # supprime AUSSI la base et les photos (à éviter)

docker compose exec web python manage.py test            # lancer les tests
docker compose exec web python manage.py shell           # console Python avec Django
docker compose exec db psql -U cotonou -d cotonou        # console SQL
docker compose exec web python manage.py spectacular --file /docs/openapi.yaml   # régénérer le contrat
```
`exec` se lance dans un **deuxième terminal**, pendant que `up` tourne dans le premier.

## Adresses et comptes de démonstration
| Quoi | Adresse |
| --- | --- |
| Documentation interactive de l'API (essayer les requêtes) | http://localhost:8000/api/docs/ |
| Santé de l'API | http://localhost:8000/api/v1/health |
| Espace mairie (admin Django) | http://localhost:8000/admin/ |

| Compte | Mot de passe | Rôle |
| --- | --- | --- |
| `admin` | `admin1234` | Administrateur : voit tout |
| `agent.dechets`, `agent.assainissement`, `agent.techniques`, `agent.eclairage`, `agent.police` | `agent1234` | Agent d'un service : ne voit que ses catégories |

Ces comptes et les 8 signalements « [démo] » sont **fictifs**, créés au démarrage tant que `SEED_DEMO=true` (développement seulement).

**Tester un endpoint réservé aux agents dans `/api/docs/`** : appeler `POST /auth/login`, copier le `token` de la réponse, cliquer sur
**Authorize**, saisir `Token <le jeton>` (avec le mot `Token` et une espace).

## Premier démarrage : à faire AVANT de coder
La première fois, Docker télécharge les images (PostGIS, Python) et installe les bibliothèques géographiques : **plusieurs minutes,
beaucoup de données**. Sur le Wi-Fi d'une salle de 15 personnes, ce sera lent. Lancez `docker compose up` dès maintenant ; les fois
suivantes, ça démarre en quelques secondes.

Le message de fin de démarrage est : `→ Prêt : API sur http://localhost:8000/api/docs/`.

## Chaque machine a sa propre base
Chaque développeur lance son propre backend et sa propre base : vos tests ne polluent pas ceux des autres. Pour **intégrer**
(front contre vrai back, démonstration finale), on pointe tous les fronts vers **une seule machine** qui héberge l'API
(son adresse IP sur le réseau local, ou un tunnel HTTPS pour WhatsApp). Un mentor désigne cette machine.

## Pour un front qui appelle l'API
- L'URL de base de l'API est `http://localhost:8000/api/v1`.
- Si le front tourne sur un autre port que 3000, ajouter son adresse à `CORS_ALLOWED_ORIGINS` dans `.env`, puis `docker compose up -d`.
- Pour développer sans attendre le back : `npx @stoplight/prism-cli mock docs/openapi.yaml` simule l'API à partir du contrat.

## Problèmes fréquents
| Symptôme | Cause et solution |
| --- | --- |
| `env file … .env not found` | Mise à jour récente de Docker Compose requise (le fichier `.env` est facultatif). En attendant : `cp .env.example .env` |
| `port is already allocated` (8000) | Mettre `WEB_PORT=8001` dans `.env`, puis `docker compose up -d` |
| `exec /usr/local/bin/entrypoint.sh: no such file or directory` | Fins de ligne Windows. Faire `docker compose up --build` ; `.gitattributes` évite le problème à la prochaine copie |
| `no matching manifest for linux/arm64` (Mac Apple Silicon) | Ajouter `platform: linux/amd64` au service `db` dans `docker-compose.yml` (plus lent, mais fonctionne) |
| Le rechargement ne se déclenche pas sous Windows | Cloner le dépôt **dans WSL2** (par exemple `~/projets`), pas dans `C:\Users\…` : bien plus rapide et fiable |
| `relation "reports_report" does not exist` | Migrations non appliquées : `docker compose restart web` |
| Un changement de `.env` n'a aucun effet | Il faut `docker compose up -d` (un simple rechargement du code ne relit pas `.env`) |
| Tout est cassé et on ne sait pas pourquoi | `docker compose down -v` puis `docker compose up` |
