"""
Traitement des messages WhatsApp reçus (ÉQUIPE 6). Voir docs/whatsapp.md.

W-1 : Normalisation du texte entrant (normalize_text, déjà dans reports/utils.py).
W-2 : Traitement et génération de session (handle_incoming → CaptureSession).
W-3 : Message d'accueil et d'aide (texte ≠ « signaler »).
W-4 : Ignorer les événements non-texte (iter_text_messages filtre déjà type=="text").
"""

import logging

from reports.models import CaptureSession, Report
from reports.utils import normalize_text, reporter_ref

from .client import mask_number, send_text

logger = logging.getLogger(__name__)

# Message d'aide renvoyé quand le citoyen écrit autre chose que « signaler » (W-3)
HELP_MESSAGE = (
    "👋 Bienvenue sur Cotonou Signale !\n"
    "Pour signaler un problème (ordures, route, éclairage…), "
    "écrivez simplement : Signaler\n"
    "Vous recevrez un lien pour prendre une photo et envoyer votre signalement."
)


def iter_text_messages(payload):
    """
    Extrait les messages texte d'un appel de Meta. Renvoie des couples (numéro_de_l_expéditeur, texte).
    Structure : payload["entry"][i]["changes"][j]["value"]["messages"][k] = {"from", "type", "text": {"body"}}.
    Les autres événements (accusés de livraison, etc.) sont ignorés sans erreur (W-4).
    """
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                if message.get("type") == "text":
                    yield message.get("from", ""), message.get("text", {}).get("body", "")


def handle_incoming(payload):
    """
    Traite chaque message texte du webhook WhatsApp :

    W-1 + W-2 : Si le texte normalisé vaut « signaler » :
        - Crée une CaptureSession (channel=whatsapp, reporter_ref=HMAC du numéro).
        - Envoie le lien de capture au citoyen.
    W-3 : Sinon, envoie un message d'aide pour orienter l'utilisateur.
    W-4 : Les événements non-texte (statuts Meta, médias) sont ignorés par iter_text_messages.

    Règle de sécurité : le numéro n'est JAMAIS journalisé en clair (mask_number).
    """
    for number, text in iter_text_messages(payload):
        masked = mask_number(number)
        logger.info("Message WhatsApp reçu de %s : %r", masked, text)

        # W-1 : normalisation (minuscules, sans accents, espaces nettoyés)
        normalized = normalize_text(text)

        if normalized == "signaler":
            # W-2 : créer la session de capture et envoyer le lien
            ref = reporter_ref(number)
            session = CaptureSession.create_for(
                channel=Report.Channel.WHATSAPP,
                reporter_ref=ref,
                phone_number=number,
            )
            capture_msg = (
                f"📸 Pour signaler un problème, ouvrez ce lien (valable 10 min) :\n"
                f"{session.capture_url}"
            )
            send_text(number, capture_msg)
            logger.info("Session de capture créée pour %s : %s", masked, session.capture_url)
        else:
            # W-3 : message d'aide
            send_text(number, HELP_MESSAGE)
