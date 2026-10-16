"""
Petits outils géographiques.

RAPPEL : un Point GeoDjango se crée avec la LONGITUDE EN PREMIER : Point(lng, lat). Le GeoJSON aussi.
"""

from math import asin, cos, radians, sin, sqrt

from django.conf import settings
from django.contrib.gis.geos import Point

EARTH_RADIUS_M = 6_371_008.8


def make_point(lat, lng):
    """Crée un point WGS84. Les paramètres sont nommés lat puis lng, le Point stocke (lng, lat)."""
    return Point(lng, lat, srid=4326)


def haversine_m(lat1, lng1, lat2, lng2):
    """Distance en mètres entre deux positions (assez précise pour des distances de quelques centaines de m)."""
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = phi2 - phi1
    dlambda = radians(lng2 - lng1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


def in_cotonou_bbox(lat, lng):
    min_lng, min_lat, max_lng, max_lat = settings.COTONOU_BBOX
    return min_lng <= lng <= max_lng and min_lat <= lat <= max_lat


def is_in_cotonou(lat, lng):
    """
    Vrai si la position est dans Cotonou. Utilise le polygone chargé avec `load_zone` s'il existe,
    sinon la boîte englobante provisoire COTONOU_BBOX.
    """
    from .models import Zone  # import tardif : évite une dépendance circulaire

    zone = Zone.objects.filter(name="Cotonou").first()
    if zone is not None:
        return zone.polygon.covers(make_point(lat, lng))
    return in_cotonou_bbox(lat, lng)
