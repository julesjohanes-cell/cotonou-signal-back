"""Vérification 6 (ÉQUIPE 5) : une photo déjà utilisée est refusée."""

from config.errors import Rejection  # noqa: F401  (à utiliser dans la vérification)


# 6 ─ Photo jamais vue ───────────────────────────────────────────────────────────────────── ⬜ À FAIRE
def check_photo_not_reused(sub):
    """
    `sub.photo_sha256` est déjà calculé (voir reports/services.py). Si un signalement a la même empreinte
    → Rejection("PHOTO_REUSED").

    Indices :
      from reports.models import Report
      Report.objects.filter(photo_sha256=sub.photo_sha256).exists()
    """
    return  # TODO équipe 5
