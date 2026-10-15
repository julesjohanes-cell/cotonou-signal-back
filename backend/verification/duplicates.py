"""Vérification 8 (ÉQUIPE 5) : un signalement identique existe déjà tout près → on fusionne (« +1 »)."""

# 8 ─ Doublon ───────────────────────────────────────────────────────────────────────────── ⬜ À FAIRE


def check_duplicate(sub):
    """
    Cherche un signalement ACTIF (statuts publiés ou en cours), de la MÊME catégorie, à moins de
    `settings.DUPLICATE_RADIUS_M` mètres du point, créé depuis moins de `settings.DUPLICATE_DAYS` jours.
    Si trouvé : `sub.duplicate_of = ce_signalement`  (le service incrémente alors `support_count`, rien d'autre à faire).

    Indices :
      from datetime import timedelta
      from django.contrib.gis.measure import D
      from django.utils import timezone
      from reports.geo import make_point
      from reports.models import Report

      Report.objects.filter(
          category=sub.category,
          status__in=[Report.Status.PUBLISHED, Report.Status.IN_PROGRESS],
          created_at__gte=timezone.now() - timedelta(days=settings.DUPLICATE_DAYS),
          location__dwithin=(make_point(sub.point_lat, sub.point_lng), D(m=settings.DUPLICATE_RADIUS_M)),
      ).first()

    Pensez à tester avec deux points distants de ~20 m et de ~200 m.
    """
    return  # TODO équipe 5
