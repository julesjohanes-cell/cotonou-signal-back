#!/bin/sh
# Démarrage du conteneur web : prépare la base, puis lance la commande demandée.
set -e

echo "→ Migrations de la base"
python manage.py migrate --noinput

echo "→ Chargement des catégories et services"
python manage.py loaddata categories

echo "→ Chargement du polygone de Cotonou"
python manage.py load_zone /docs/cotonou.geojson || echo "  (pas de fichier /docs/cotonou.geojson — bbox provisoire)"

if [ "${SEED_DEMO:-true}" = "true" ]; then
    echo "→ Données de démonstration (comptes agents et signalements fictifs)"
    python manage.py seed_demo
fi

echo "→ Prêt : API sur http://localhost:8000/api/docs/  ·  admin sur http://localhost:8000/admin/"
exec "$@"
