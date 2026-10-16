import hashlib
import hmac


def verify_signature(raw_body, header, secret):
    """
    Vérifie l'en-tête `X-Hub-Signature-256` envoyé par Meta : « sha256=<HMAC-SHA256 du corps brut> ».
    À faire AVANT de traiter la moindre donnée. `raw_body` = les octets exacts reçus (pas le JSON reparsé).
    """
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[len("sha256="):])
