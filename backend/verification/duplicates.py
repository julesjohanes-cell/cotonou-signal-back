"""Vérification 8 (ÉQUIPE 5) : un signalement identique existe déjà tout près → on fusionne (« +1 »)."""

from datetime import timedelta

from django.conf import settings
from django.contrib.gis.measure import D
from django.utils import timezone

from reports.geo import make_point
from reports.models import Report


# 8 ─ Doublon ───────────────────────────────────────────────────────────────────────────── ✅ FAIT
def check_duplicate(sub):
    """
    Cherche un signalement ACTIF (statuts publiés ou en cours), de la MÊME catégorie, à moins de
    `settings.DUPLICATE_RADIUS_M` mètres du point, créé depuis moins de `settings.DUPLICATE_DAYS` jours.
    Si trouvé : `sub.duplicate_of = ce_signalement`  (le service incrémente alors `support_count`, rien d'autre à faire).
    On ne lève rien : un doublon n'est pas un rejet, c'est une fusion.
    """
    existing = (
        Report.objects.filter(
            category=sub.category,
            status__in=[Report.Status.PUBLISHED, Report.Status.IN_PROGRESS],
            created_at__gte=timezone.now() - timedelta(days=settings.DUPLICATE_DAYS),
            location__dwithin=(make_point(sub.point_lat, sub.point_lng), D(m=settings.DUPLICATE_RADIUS_M)),
        )
        .order_by("-created_at", "-id")
        .first()
    )
    if existing is not None:
        sub.duplicate_of = existing
