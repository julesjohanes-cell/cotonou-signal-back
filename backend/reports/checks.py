"""
Vérifications 1 à 5 d'un signalement (ÉQUIPE 4). Voir docs/verification.md.

Règle : une vérification reçoit la `Submission`, ne renvoie rien, et lève `Rejection("CODE", ...)` si elle refuse.
Le message par défaut de chaque code est dans config/errors.py ; `details` est facultatif.
Les seuils viennent de `django.conf.settings` (jamais en dur ici).

État actuel :  1 ✅ faite   2 ⬜ à faire   3 ⬜ à faire   4 ⬜ à faire   5 ✅ faite (exemple de référence)
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
    from PIL import Image, UnidentifiedImageError

    max_bytes = int(settings.MAX_PHOTO_MB * 1024 * 1024)
    if sub.photo.size > max_bytes:
        raise Rejection(
            "PHOTO_INVALID",
            f"La photo est trop volumineuse ({round(sub.photo.size / (1024 * 1024), 1)} Mo, maximum autorisé : {settings.MAX_PHOTO_MB} Mo).",
            {"size_bytes": sub.photo.size, "max_bytes": max_bytes},
            status=415,
        )

    try:
        sub.photo.seek(0)
        img = Image.open(sub.photo)
        img_format = (img.format or "").upper()
        if img_format not in settings.ALLOWED_PHOTO_FORMATS:
            raise Rejection(
                "PHOTO_INVALID",
                "Format de photo non accepté. Formats autorisés : JPEG, PNG ou WebP.",
                {"format": img_format, "allowed": list(settings.ALLOWED_PHOTO_FORMATS)},
                status=415,
            )
        img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise Rejection(
            "PHOTO_INVALID",
            "La photo est illisible ou corrompue. Formats acceptés : JPEG, PNG ou WebP.",
            status=415,
        )
    finally:
        sub.photo.seek(0)


# 3 ─ Précision GPS ──────────────────────────────────────────────────────────────────────── ✅ FAIT
def check_gps_accuracy(sub):
    """
    Si `sub.device_accuracy_m` > `settings.GPS_MAX_ACCURACY_M` → Rejection("GPS_INACCURATE").
    Ajouter `{"accuracy_m": ..., "max_m": ...}` dans `details` aide le front à expliquer le refus.
    """
    if sub.device_accuracy_m > settings.GPS_MAX_ACCURACY_M:
        raise Rejection(
            "GPS_INACCURATE",
            f"Votre position GPS n'est pas assez précise ({round(sub.device_accuracy_m)} m, maximum autorisé : {int(settings.GPS_MAX_ACCURACY_M)} m). Attendez quelques secondes ou déplacez-vous.",
            {
                "accuracy_m": round(sub.device_accuracy_m),
                "max_m": int(settings.GPS_MAX_ACCURACY_M),
            },
        )


# 4 ─ Dans Cotonou ───────────────────────────────────────────────────────────────────────── ✅ FAIT
def check_zone(sub):
    """
    La position du TÉLÉPHONE doit être dans Cotonou → sinon Rejection("OUT_OF_ZONE").
    Outil prêt à l'emploi : `from reports.geo import is_in_cotonou` ; `is_in_cotonou(lat, lng)` renvoie un booléen
    (polygone chargé avec `load_zone` si disponible, sinon boîte englobante provisoire).
    """
    from reports.geo import is_in_cotonou

    if not is_in_cotonou(sub.device_lat, sub.device_lng):
        raise Rejection(
            "OUT_OF_ZONE",
            "Votre position se trouve en dehors de Cotonou. Les signalements ne sont acceptés que sur le territoire de la commune.",
            {
                "device_lat": sub.device_lat,
                "device_lng": sub.device_lng,
            },
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
