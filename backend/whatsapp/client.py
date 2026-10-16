"""
Envoi de messages WhatsApp. `WHATSAPP_MODE=mock` (défaut) : le message est écrit dans les logs au lieu d'être
envoyé, donc tout peut être testé sans compte Meta.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def mask_number(number):
    """229****1234 : un numéro de téléphone n'apparaît JAMAIS en clair dans les logs."""
    digits = "".join(c for c in (number or "") if c.isdigit())
    return f"{digits[:3]}****{digits[-4:]}" if len(digits) > 7 else "****"


def send_text(to, body):
    if settings.WHATSAPP_MODE == "mock":
        logger.info("[WhatsApp simulé] vers %s : %s", mask_number(to), body)
        return
    # ⬜ À FAIRE (équipe 6) pour le mode live :
    #   POST https://graph.facebook.com/<version>/<WHATSAPP_PHONE_NUMBER_ID>/messages
    #   en-tête  Authorization: Bearer <WHATSAPP_ACCESS_TOKEN>
    #   corps    {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": body}}
    #   (voir la documentation Meta pour la version courante de l'API)
    raise NotImplementedError("Envoi WhatsApp live à implémenter par l'équipe 6.")
