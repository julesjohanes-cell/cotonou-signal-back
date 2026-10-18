"""Vérification 6 (ÉQUIPE 5) : une photo déjà utilisée est refusée."""

from config.errors import Rejection


# 6 ─ Photo jamais vue ───────────────────────────────────────────────────────────────────── ✅ FAIT
def check_photo_not_reused(sub):
    """
    `sub.photo_sha256` est déjà calculé (voir reports/services.py). Si un signalement a la même empreinte
    → Rejection("PHOTO_REUSED").
    """
    from reports.models import Report

    if sub.photo_sha256 and Report.objects.filter(photo_sha256=sub.photo_sha256).exists():
        raise Rejection("PHOTO_REUSED")
