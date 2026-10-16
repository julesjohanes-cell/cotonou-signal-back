"""
Traitement des messages WhatsApp reçus (ÉQUIPE 6). Voir docs/whatsapp.md.
"""

import logging

from reports.utils import normalize_text, reporter_ref  # noqa: F401  (à utiliser dans handle_incoming)

from .client import send_text  # noqa: F401  (à utiliser dans handle_incoming)

logger = logging.getLogger(__name__)


def iter_text_messages(payload):
    """
    Extrait les messages texte d'un appel de Meta. Renvoie des couples (numéro_de_l_expéditeur, texte).
    Structure : payload["entry"][i]["changes"][j]["value"]["messages"][k] = {"from", "type", "text": {"body"}}.
    Les autres événements (accusés de livraison, etc.) sont ignorés sans erreur.
    """
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                if message.get("type") == "text":
                    yield message.get("from", ""), message.get("text", {}).get("body", "")


# ⬜ À FAIRE (équipe 6) ─────────────────────────────────────────────────────────────────────────────────────
def handle_incoming(payload):
    """
    Pour chaque message texte (voir iter_text_messages) :
      1. si `normalize_text(texte) == "signaler"` :
           session = CaptureSession.create_for(channel="whatsapp", reporter_ref=reporter_ref(numero))
           send_text(numero, f"Pour signaler un problème, ouvrez ce lien (valable 10 min) : {session.capture_url}")
      2. sinon : répondre avec un court message d'aide (« Écrivez Signaler pour commencer »).
    Ne jamais journaliser ni stocker le numéro en clair (utiliser reporter_ref).
    Plus tard : envoyer la confirmation + le code de suivi dans la discussion après la vérification.
    """
    for number, text in iter_text_messages(payload):
        logger.info("Message WhatsApp reçu (traitement à implémenter) de %s", "****")
