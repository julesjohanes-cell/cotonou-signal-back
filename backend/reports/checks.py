"""
Vérifications 1 à 5 d'un signalement (ÉQUIPE 4). Voir docs/verification.md.

Règle : une vérification reçoit la `Submission`, ne renvoie rien, et lève `Rejection("CODE", ...)` si elle refuse.
Le message par défaut de chaque code est dans config/errors.py ; `details` est facultatif.
Les seuils viennent de `django.conf.settings` (jamais en dur ici).

État actuel :  1 ✅ faite   2 ✅ faite   3 ✅ faite   4 ✅ faite   5 ✅ faite
"""

from django.conf import settings

from config.errors import ApiError, Rejection


# 1 ─ Lien de capture valide ───────────────────────────────────────────────────────────────── ✅ FAIT
def check_token(sub):
    if not sub.capture_token:
        if settings.REQUIRE_CAPTURE_TOKEN:
            raise ApiError(
                "INVALID_INPUT",
                "Un lien de capture est nécessaire pour envoyer un signalement.",
                {"fields": {"capture_token": ["Ce champ est obligatoire."]}},
            )
        return
    if sub.capture_session is None:
        raise ApiError("NOT_FOUND", "Ce lien de signalement est inconnu.")
    sub.capture_session.assert_usable()  # lève TOKEN_USED ou TOKEN_EXPIRED


# 2 ─ Photo lisible ─────────────────────────────────────────────────────────────────────── ✅ FAIT
def check_photo_file(sub):
    """
    JPEG, PNG ou WebP, taille ≤ MAX_PHOTO_MB, fichier lisible → sinon Rejection("PHOTO_INVALID") (HTTP 415).
    """
    max_bytes = settings.MAX_PHOTO_MB * 1024 * 1024
    if sub.photo.size > max_bytes:
        raise Rejection(
            "PHOTO_INVALID",
            f"La photo est trop lourde (max {settings.MAX_PHOTO_MB} Mo).",
            {"size_mb": round(sub.photo.size / (1024 * 1024), 1), "max_mb": settings.MAX_PHOTO_MB},
        )
    try:
        from PIL import Image

        img = Image.open(sub.photo)
        img.verify()
    except Exception:
        sub.photo.seek(0)
        raise Rejection("PHOTO_INVALID", "La photo est illisible ou son format n'est pas accepté.")
    if img.format not in settings.ALLOWED_PHOTO_FORMATS:
        sub.photo.seek(0)
        raise Rejection(
            "PHOTO_INVALID",
            f"Format non accepté (formats autorisés : {', '.join(settings.ALLOWED_PHOTO_FORMATS)}).",
        )
    sub.photo.seek(0)


# 3 ─ Précision GPS ──────────────────────────────────────────────────────────────────────── ✅ FAIT
def check_gps_accuracy(sub):
    """
    Si `sub.device_accuracy_m` > `settings.GPS_MAX_ACCURACY_M` → Rejection("GPS_INACCURATE").
    """
    if sub.device_accuracy_m > settings.GPS_MAX_ACCURACY_M:
        raise Rejection(
            "GPS_INACCURATE",
            f"Votre précision GPS est de {sub.device_accuracy_m:.0f} m (maximum {int(settings.GPS_MAX_ACCURACY_M)} m).",
            {"accuracy_m": sub.device_accuracy_m, "max_m": int(settings.GPS_MAX_ACCURACY_M)},
        )


# 4 ─ Dans Cotonou ───────────────────────────────────────────────────────────────────────── ✅ FAIT
def check_zone(sub):
    """
    La position du TÉLÉPHONE doit être dans Cotonou → sinon Rejection("OUT_OF_ZONE").
    """
    from reports.geo import is_in_cotonou

    if not is_in_cotonou(sub.device_lat, sub.device_lng):
        raise Rejection(
            "OUT_OF_ZONE",
            "Vous semblez être en dehors de Cotonou. Le point doit être dans la zone couverte.",
        )


# 5 ─ Distance point / téléphone ─────────────────────────────────────────────────── ✅ FAIT (modèle à suivre)
def check_distance(sub):
    distance = sub.distance_m
    if distance > settings.MAX_DISTANCE_M:
        raise Rejection(
            "TOO_FAR",
            f"Le point est à plus de {int(settings.MAX_DISTANCE_M)} m de votre position.",
            {"distance_m": round(distance), "max_m": int(settings.MAX_DISTANCE_M)},
        )
