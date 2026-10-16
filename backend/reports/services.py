"""
Logique métier de la création d'un signalement (appelée par la vue POST /reports).
Les vues restent minces : validation des champs dans les serializers, règles dans les vérifications.
"""

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from verification.pipeline import run_pipeline
from verification.submission import Submission

from .geo import make_point
from .models import CaptureSession, Report, StatusChange
from .utils import sha256_of_file


@transaction.atomic
def create_report(data):
    """
    `data` : dictionnaire validé par ReportCreateSerializer.
    Renvoie `(report, is_duplicate)`. Lève `Rejection` si une vérification refuse (rien n'est alors enregistré
    et le lien de capture n'est PAS consommé : le citoyen peut corriger et réessayer).
    """
    token = data.get("capture_token") or ""
    session = None
    if token:
        # Verrou de ligne : deux envois simultanés avec le même lien ne peuvent pas passer tous les deux
        session = CaptureSession.objects.select_for_update().filter(token=token).first()

    submission = Submission(
        category=data["category"],
        description=data.get("description", ""),
        photo=data["photo"],
        point_lat=data["point_lat"],
        point_lng=data["point_lng"],
        device_lat=data["device_lat"],
        device_lng=data["device_lng"],
        device_accuracy_m=data["device_accuracy_m"],
        channel=session.channel if session else Report.Channel.WEB,
        capture_token=token,
        capture_session=session,
    )
    submission.photo_sha256 = sha256_of_file(submission.photo)

    run_pipeline(submission)  # lève Rejection si une vérification refuse

    if session is not None:
        session.used_at = timezone.now()
        session.save(update_fields=["used_at"])

    if submission.duplicate_of is not None:
        Report.objects.filter(pk=submission.duplicate_of.pk).update(support_count=F("support_count") + 1)
        submission.duplicate_of.refresh_from_db()
        return submission.duplicate_of, True

    status = Report.Status.MODERATION if submission.category.needs_moderation else Report.Status.PUBLISHED
    report = Report.objects.create(
        tracking_code=Report.generate_tracking_code(),
        category=submission.category,
        description=submission.description,
        status=status,
        channel=submission.channel,
        location=make_point(submission.point_lat, submission.point_lng),
        reporter_location=make_point(submission.device_lat, submission.device_lng),
        reporter_accuracy_m=submission.device_accuracy_m,
        distance_m=submission.distance_m,
        photo=submission.photo,
        photo_sha256=submission.photo_sha256,
        ai_verdict=submission.ai_verdict,
        reporter_ref=session.reporter_ref if session else "",
    )
    StatusChange.objects.create(report=report, from_status="", to_status=status, note="Signalement reçu")
    return report, False
