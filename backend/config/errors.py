"""
Format d'erreur unique de l'API (voir docs/api-contract.md) :

    {"error": {"code": "TOO_FAR", "message": "…en français…", "details": {}}}

Pour refuser une requête depuis n'importe quel endroit du code, lever `ApiError(code, ...)` ou, pour un rejet
par une vérification (HTTP 422), `Rejection(code, ...)`. Le message par défaut vient de MESSAGES.
"""

from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler

# Code → (statut HTTP, message par défaut lisible par un citoyen)
CODES = {
    "INVALID_INPUT": (400, "Certaines informations sont manquantes ou incorrectes."),
    "UNAUTHENTICATED": (401, "Connexion requise."),
    "FORBIDDEN": (403, "Vous n'avez pas le droit d'effectuer cette action."),
    "NOT_FOUND": (404, "Élément introuvable."),
    "TOKEN_USED": (409, "Ce lien de signalement a déjà été utilisé. Demandez-en un nouveau."),
    "INVALID_TRANSITION": (409, "Ce changement de statut n'est pas autorisé."),
    "TOKEN_EXPIRED": (410, "Ce lien de signalement a expiré. Demandez-en un nouveau."),
    "PHOTO_INVALID": (415, "La photo est illisible ou son format n'est pas accepté (JPEG, PNG ou WebP)."),
    "OUT_OF_ZONE": (422, "Vous semblez être en dehors de Cotonou."),
    "TOO_FAR": (422, "Le point est trop loin de votre position."),
    "GPS_INACCURATE": (422, "Votre position GPS n'est pas assez précise. Attendez quelques secondes ou déplacez-vous."),
    "PHOTO_REUSED": (422, "Cette photo a déjà été utilisée pour un autre signalement."),
    "PHOTO_MISMATCH": (422, "La photo ne correspond pas à la catégorie choisie."),
    "PHOTO_SCREENSHOT": (422, "Les captures d'écran ne sont pas acceptées. Prenez la photo sur place."),
    "RATE_LIMITED": (429, "Trop de requêtes. Réessayez dans un instant."),
}


class ApiError(Exception):
    """Erreur de l'API, convertie en réponse JSON au format du contrat."""

    def __init__(self, code, message=None, details=None, status=None):
        default_status, default_message = CODES.get(code, (400, "Erreur."))
        self.code = code
        self.message = message or default_message
        self.details = details or {}
        self.status = status or default_status
        super().__init__(self.message)


class Rejection(ApiError):
    """Un signalement refusé par une vérification (HTTP 422 par défaut, selon le code)."""


def error_response(code, message, details=None, status=400):
    return Response(
        {"error": {"code": code, "message": message, "details": details or {}}},
        status=status,
    )


def api_exception_handler(exc, context):
    """Convertit toutes les erreurs DRF au format du contrat."""
    if isinstance(exc, ApiError):
        return error_response(exc.code, exc.message, exc.details, exc.status)
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()

    response = exception_handler(exc, context)
    if response is None:
        return None  # erreur inattendue : Django affiche l'erreur 500 (utile pour déboguer)

    if isinstance(exc, exceptions.ValidationError):
        return error_response("INVALID_INPUT", CODES["INVALID_INPUT"][1], {"fields": response.data}, 400)
    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        return error_response("UNAUTHENTICATED", CODES["UNAUTHENTICATED"][1], status=401)
    if isinstance(exc, exceptions.PermissionDenied):
        return error_response("FORBIDDEN", CODES["FORBIDDEN"][1], status=403)
    if isinstance(exc, exceptions.NotFound):
        return error_response("NOT_FOUND", CODES["NOT_FOUND"][1], status=404)
    if isinstance(exc, exceptions.Throttled):
        details = {"retry_after_s": exc.wait} if exc.wait else {}
        return error_response("RATE_LIMITED", CODES["RATE_LIMITED"][1], details, 429)
    if isinstance(exc, exceptions.UnsupportedMediaType):
        return error_response("INVALID_INPUT", "Format de requête non pris en charge.", status=415)
    if isinstance(exc, exceptions.ParseError):
        return error_response("INVALID_INPUT", "Requête illisible.", status=400)
    if isinstance(exc, exceptions.MethodNotAllowed):
        return error_response("NOT_FOUND", "Méthode non autorisée pour cette adresse.", status=405)
    return response
