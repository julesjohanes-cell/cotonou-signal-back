"""
Envoi de messages WhatsApp. `WHATSAPP_MODE=mock` (défaut) : le message est écrit dans les logs au lieu d'être
envoyé, donc tout peut être testé sans compte Meta.

W-5 : send_confirmation — notification de suivi après validation d'un signalement WhatsApp.
"""

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

# Version de l'API Meta Cloud utilisée (à mettre à jour selon la doc Meta)
META_API_VERSION = "v21.0"


def mask_number(number):
    """229****1234 : un numéro de téléphone n'apparaît JAMAIS en clair dans les logs."""
    digits = "".join(c for c in (number or "") if c.isdigit())
    return f"{digits[:3]}****{digits[-4:]}" if len(digits) > 7 else "****"


def send_text(to, body):
    """Envoie un message texte WhatsApp. Mode mock → logs uniquement. Mode live → appel API Meta."""
    if settings.WHATSAPP_MODE == "mock":
        logger.info("[WhatsApp simulé] vers %s : %s", mask_number(to), body)
        return

    # Mode live : appel HTTP vers l'API Meta Cloud
    url = (
        f"https://graph.facebook.com/{META_API_VERSION}"
        f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=settings.AI_TIMEOUT_S) as resp:
            logger.info(
                "[WhatsApp live] message envoyé à %s (HTTP %d)",
                mask_number(to), resp.status,
            )
    except (urllib.error.URLError, OSError) as exc:
        # Ne jamais faire planter le serveur si l'envoi échoue ; logger l'erreur et continuer
        logger.error("[WhatsApp live] échec d'envoi à %s : %s", mask_number(to), exc)


def send_confirmation(to, tracking_code):
    """
    W-5 : Notifie le citoyen sur WhatsApp que son signalement est enregistré.

    Message : « Votre signalement a été enregistré avec le code de suivi : CS-XXXXXX.
    Suivez son avancement sur <FRONT_URL>/suivi/CS-XXXXXX ».
    """
    tracking_url = f"{settings.FRONT_URL.rstrip('/')}/suivi/{tracking_code}"
    body = (
        f"✅ Votre signalement a été enregistré avec le code de suivi : {tracking_code}.\n"
        f"Suivez son avancement sur {tracking_url}"
    )
    send_text(to, body)
