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

from config.errors import Rejection  # noqa: F401  (à utiliser dans la vérification)

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


# 7 ─ Contenu de la photo ────────────────────────────────────────────────────────────────── ⬜ À FAIRE
def check_photo_content(sub):
    """
    1. `verdict = get_client().verify(octets_de_la_photo, sub.photo.name, sub.category.label)`
       (lire les octets avec `sub.photo.read()` puis `sub.photo.seek(0)`)
    2. Stocker le verdict : `sub.ai_verdict = verdict`
    3. Refuser :
         - capture d'écran            → Rejection("PHOTO_SCREENSHOT")
         - ne correspond pas / confiance < settings.AI_MIN_CONFIDENCE → Rejection("PHOTO_MISMATCH")
    4. Réponse mal formée ou délai dépassé : NE PAS deviner. Décision à prendre avec l'équipe (voir docs/verification.md).
    Ne jamais renvoyer `reason` ni le verdict au public.
    """
    return  # TODO équipe 5
