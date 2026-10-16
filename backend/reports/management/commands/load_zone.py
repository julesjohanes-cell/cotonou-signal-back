"""
Charge le polygone de Cotonou depuis un fichier GeoJSON (par exemple exporté d'OpenStreetMap).

    docker compose exec web python manage.py load_zone /docs/cotonou.geojson

(le dossier docs/ du dépôt est visible dans le conteneur sous /docs)
"""

import json

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.core.management.base import BaseCommand, CommandError

from reports.models import Zone


class Command(BaseCommand):
    help = "Charge le polygone d'une zone (Cotonou par défaut) depuis un fichier GeoJSON."

    def add_arguments(self, parser):
        parser.add_argument("geojson_path")
        parser.add_argument("--name", default="Cotonou")

    def handle(self, *args, **options):
        with open(options["geojson_path"], encoding="utf-8") as handle:
            data = json.load(handle)

        geometries = []
        if data.get("type") == "FeatureCollection":
            geometries = [f["geometry"] for f in data.get("features", []) if f.get("geometry")]
        elif data.get("type") == "Feature":
            geometries = [data["geometry"]]
        else:
            geometries = [data]

        polygons = []
        for geometry in geometries:
            geos = GEOSGeometry(json.dumps(geometry), srid=4326)
            if geos.geom_type == "Polygon":
                polygons.append(geos)
            elif geos.geom_type == "MultiPolygon":
                polygons.extend(list(geos))
        if not polygons:
            raise CommandError("Aucun polygone trouvé dans ce fichier.")

        zone, created = Zone.objects.update_or_create(
            name=options["name"], defaults={"polygon": MultiPolygon(*polygons, srid=4326)}
        )
        verb = "créée" if created else "mise à jour"
        self.stdout.write(self.style.SUCCESS(f"Zone « {zone.name} » {verb} ({len(polygons)} polygone(s))."))
