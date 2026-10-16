"""
Vérification 7 (ÉQUIPE 5) : le modèle de vision confirme que la photo montre la catégorie déclarée.

`VERIFY_MODE=mock` (défaut) : verdict simulé, aucune clé nécessaire → le front et la démonstration ne dépendent
jamais d'un quota. `VERIFY_MODE=live` : appelle le vrai modèle (à brancher dans LiveVisionClient).

Le prompt de départ est dans docs/verification.md. La réponse attendue du modèle est un JSON strict :
{matches_category, is_screenshot_or_screen_photo, is_public_outdoor_space, contains_identifiable_person,
 confidence, reason}.
"""

import logging

from django.conf import settings

from config.errors import Rejection

logger = logging.getLogger(__name__)


class MockVisionClient:
    """Verdict prévisible : tout est accepté, sauf un fichier dont le nom contient « screenshot » ou « capture »."""

    def verify(self, photo_bytes, filename, category_label):
        name = (filename or "").lower()
        is_screenshot = "screenshot" in name or "capture" in name
        return {
            "matches_category": not is_screenshot,
            "is_screenshot_or_screen_photo": is_screenshot,
            "is_public_outdoor_space": True,
            "contains_identifiable_person": False,
            "confidence": 0.9,
            "reason": "Verdict simulé (VERIFY_MODE=mock).",
        }


class LiveVisionClient:
    """À implémenter par l'équipe 5 : envoyer l'image + le prompt au modèle, analyser le JSON STRICTEMENT."""

    def verify(self, photo_bytes, filename, category_label):
        raise NotImplementedError(
            "Brancher le vrai modèle de vision ici (clé dans VISION_API_KEY, délai max settings.AI_TIMEOUT_S)."
        )


def get_client():
    return LiveVisionClient() if settings.VERIFY_MODE == "live" else MockVisionClient()


# 7 ─ Contenu de la photo ────────────────────────────────────────────────────────────────── ✅ FAIT (base)
def check_photo_content(sub):
    """
    1. `verdict = get_client().verify(octets_de_la_photo, sub.photo.name, sub.category.label)`
    2. Stocker le verdict : `sub.ai_verdict = verdict` (jamais exposé au public, avec sa `reason`)
    3. Refuser :
         - capture d'écran → Rejection("PHOTO_SCREENSHOT")
         - (V-5) ne correspond pas ou confiance < settings.AI_MIN_CONFIDENCE → Rejection("PHOTO_MISMATCH")
    """
    sub.photo.seek(0)
    verdict = get_client().verify(sub.photo.read(), sub.photo.name, sub.category.label)
    sub.photo.seek(0)  # remet le curseur : la photo sera sauvegardée ensuite (services.py)
    sub.ai_verdict = verdict
    if verdict.get("is_screenshot_or_screen_photo"):
        raise Rejection("PHOTO_SCREENSHOT")
