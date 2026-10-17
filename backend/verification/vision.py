"""
Vérification 7 (ÉQUIPE 5) : le modèle de vision confirme que la photo montre la catégorie déclarée.

`VERIFY_MODE=mock` (défaut) : verdict simulé, aucune clé nécessaire → le front et la démonstration ne dépendent
jamais d'un quota. `VERIFY_MODE=live` : appelle le vrai modèle (à brancher dans LiveVisionClient).

Le prompt de départ est dans docs/verification.md. La réponse attendue du modèle est un JSON strict :
{matches_category, is_screenshot_or_screen_photo, is_public_outdoor_space, contains_identifiable_person,
 confidence, reason}.
"""

import base64
import json
import logging
import urllib.request

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


class VisionError(Exception):
    """Verdict IA indisponible : réponse mal formée, délai dépassé ou erreur réseau. On ne devine jamais."""


# Modèle choisi par les mentors (Qwen ; le format « qwen/… » est la convention OpenRouter, API compatible
# OpenAI). Si la clé est plutôt un compte Bailian/DashScope, ne changer QUE VISION_ENDPOINT.
VISION_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
VISION_MODEL = "qwen/qwen3.8-27b"

# Prompt de docs/verification.md (la réponse attendue est un objet JSON strict à 6 clés)
VISION_PROMPT_TEMPLATE = (
    "Tu vérifies un signalement citoyen d'insalubrité à Cotonou.\n"
    "Catégorie déclarée : {label}.\n"
    "Réponds uniquement par un objet JSON, sans autre texte :\n"
    "{{\n"
    '  "matches_category": true ou false,\n'
    '  "is_screenshot_or_screen_photo": true ou false,\n'
    '  "is_public_outdoor_space": true ou false,\n'
    '  "contains_identifiable_person": true ou false,\n'
    '  "confidence": nombre entre 0 et 1,\n'
    '  "reason": "une phrase en français"\n'
    "}}\n"
    "Si l'image est une capture d'écran, une photo d'un écran, un dessin ou n'a aucun rapport "
    "avec la catégorie, matches_category vaut false."
)

# Les 6 clés attendues et leurs types (vérifiés STRICTEMENT : toute réponse mal formée est un échec)
_EXPECTED_VERDICT_KEYS = {
    "matches_category": bool,
    "is_screenshot_or_screen_photo": bool,
    "is_public_outdoor_space": bool,
    "contains_identifiable_person": bool,
    "confidence": (int, float),
    "reason": str,
}


def _image_data_url(photo_bytes, filename):
    """Photo en data URL base64 (le MIME est déduit de l'extension, JPEG par défaut)."""
    extension = (filename or "").rsplit(".", 1)[-1].lower()
    content_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        extension, "image/jpeg"
    )
    return "data:{};base64,{}".format(content_type, base64.b64encode(photo_bytes).decode("ascii"))


def _post_json(url, payload, api_key, timeout):
    """POST JSON avec la stdlib (aucune dépendance) : renvoie le corps de la réponse analysé.
    Laisse propager les exceptions réseau et de délai (OSError : HTTPError, socket.timeout)."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer {}".format(api_key),
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _validate_verdict(verdict):
    """JSON strict : les 6 clés exactes, types conformes, confiance dans [0, 1]. Sinon VisionError."""
    if not isinstance(verdict, dict):
        raise VisionError("réponse du modèle : attendu un objet JSON")
    for key, expected in _EXPECTED_VERDICT_KEYS.items():
        value = verdict.get(key)
        if isinstance(value, bool) and expected is not bool:
            raise VisionError("réponse du modèle : clé {} de mauvais type".format(key))
        if not isinstance(value, expected):
            raise VisionError("réponse du modèle : clé {} absente ou de mauvais type".format(key))
    if not 0 <= verdict["confidence"] <= 1:
        raise VisionError("réponse du modèle : confiance hors de [0, 1]")


class LiveVisionClient:
    """Vrai modèle de vision (Qwen, API compatible OpenAI). La clé vient de l'environnement, jamais du code."""

    def verify(self, photo_bytes, filename, category_label):
        payload = {
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT_TEMPLATE.format(label=category_label)},
                        {"type": "image_url", "image_url": {"url": _image_data_url(photo_bytes, filename)}},
                    ],
                }
            ],
        }
        try:
            body = _post_json(VISION_ENDPOINT, payload, settings.VISION_API_KEY, settings.AI_TIMEOUT_S)
            content = body["choices"][0]["message"]["content"]
            verdict = json.loads(content)
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            # HTTPError et socket.timeout sont des OSError ; JSONDecodeError est un ValueError
            raise VisionError("verdict IA inaccessible ({})".format(type(exc).__name__)) from exc
        _validate_verdict(verdict)
        return verdict


def get_client():
    return LiveVisionClient() if settings.VERIFY_MODE == "live" else MockVisionClient()


# 7 ─ Contenu de la photo ────────────────────────────────────────────────────────────────── ✅ FAIT
def check_photo_content(sub):
    """
    1. `verdict = get_client().verify(octets_de_la_photo, sub.photo.name, sub.category.label)`
    2. Stocker le verdict : `sub.ai_verdict = verdict` (jamais exposé au public, avec sa `reason`)
    3. Refuser :
         - capture d'écran → Rejection("PHOTO_SCREENSHOT")
         - ne correspond pas ou confiance < settings.AI_MIN_CONFIDENCE → Rejection("PHOTO_MISMATCH")
    """
    sub.photo.seek(0)
    try:
        verdict = get_client().verify(sub.photo.read(), sub.photo.name, sub.category.label)
    except VisionError:
        # Échec IA (réponse mal formée ou délai dépassé) : on ne devine pas, on refuse proprement.
        # À revoir avec le mentor selon la décision M-2 (recommandation : garder en « pending »).
        logger.warning("Verdict IA indisponible : signalement refusé sans verdict.")
        sub.photo.seek(0)
        raise Rejection(
            "PHOTO_MISMATCH", "Nous n'avons pas pu vérifier votre photo. Réessayez dans un instant."
        )
    sub.photo.seek(0)  # remet le curseur : la photo sera sauvegardée ensuite (services.py)
    sub.ai_verdict = verdict
    if verdict.get("is_screenshot_or_screen_photo"):
        raise Rejection("PHOTO_SCREENSHOT")
    if not verdict.get("matches_category") or verdict.get("confidence") < settings.AI_MIN_CONFIDENCE:
        raise Rejection("PHOTO_MISMATCH")
