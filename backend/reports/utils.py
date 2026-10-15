import hashlib
import hmac
import re
import unicodedata

from django.conf import settings


def sha256_of_file(uploaded_file):
    """Empreinte SHA-256 du contenu d'un fichier envoyé (le curseur est remis au début)."""
    digest = hashlib.sha256()
    uploaded_file.seek(0)
    for chunk in iter(lambda: uploaded_file.read(1024 * 1024), b""):
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


def reporter_ref(phone_number):
    """Identifiant anonyme (HMAC) d'un numéro de téléphone. Le numéro lui-même n'est JAMAIS stocké."""
    digits = re.sub(r"\D", "", phone_number or "")
    if not digits:
        return ""
    return hmac.new(
        settings.REPORTER_HMAC_KEY.encode(), digits.encode(), hashlib.sha256
    ).hexdigest()[:32]


def normalize_text(text):
    """Minuscules, sans accents, espaces nettoyés : « Signaler  » → « signaler »."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.lower().split())
