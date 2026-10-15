"""
La suite de vérifications d'un signalement, dans l'ordre (le moins coûteux d'abord).
Chaque étape vit dans son propre fichier pour que les équipes ne se marchent pas dessus :

    équipe 4 → reports/checks.py          (étapes 1 à 5)
    équipe 5 → verification/*.py          (étapes 6 à 8)

Pour réordonner ou ajouter une étape, modifier uniquement la liste STEPS.
"""

from reports import checks
from verification import duplicates, photo_hash, vision

STEPS = [
    checks.check_token,  # 1 lien de capture valide
    checks.check_photo_file,  # 2 photo lisible
    checks.check_gps_accuracy,  # 3 précision GPS
    checks.check_zone,  # 4 dans Cotonou
    checks.check_distance,  # 5 point à moins de 100 m du téléphone
    photo_hash.check_photo_not_reused,  # 6 photo jamais vue
    vision.check_photo_content,  # 7 modèle de vision
    duplicates.check_duplicate,  # 8 doublon → +1
]


def run_pipeline(submission):
    """Exécute les étapes dans l'ordre ; la première qui refuse lève une `Rejection`."""
    for step in STEPS:
        step(submission)
    return submission
