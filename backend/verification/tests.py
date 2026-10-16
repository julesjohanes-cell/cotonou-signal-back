"""
Tests de la vérification 8 — doublon (ÉQUIPE 5). Lancer :  docker compose exec web python manage.py test verification

La base de tests est réutilisée depuis reports/tests.py (ApiTestCase, photo_file) pour ne pas dupliquer
les aides d'envoi. Les coordonnées repartent de POINT : à 6° de latitude, 1° de longitude ≈ 110 600 m,
donc Δlng ≈ 0,00018 ≈ 20 m et Δlng ≈ 0,0018 ≈ 200 m.
"""

from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from reports.models import Report
from reports.tests import ApiTestCase, photo_file


def fake_verdict(**overrides):
    """Verdict de base pour les tests de seuil (même structure que la réponse du modèle de vision)."""
    verdict = {
        "matches_category": True,
        "is_screenshot_or_screen_photo": False,
        "is_public_outdoor_space": True,
        "contains_identifiable_person": False,
        "confidence": 0.9,
        "reason": "Verdict de test.",
    }
    verdict.update(overrides)
    return verdict


class FakeVisionClient:
    """Client renvoyant un verdict fixe (le client simulé est bloqué à 0,9)."""

    def __init__(self, verdict):
        self.verdict = verdict

    def verify(self, photo_bytes, filename, category_label):
        return self.verdict


class DuplicateCheckTest(ApiTestCase):
    """Deux points proches (20 m), même catégorie → fusion (+1). Loin (200 m) → nouveau signalement."""

    def test_close_same_category_is_merged(self):
        first = self.post_report()
        self.assertEqual(first.status_code, 201, first.content)
        self.assertFalse(first.json()["duplicate"])
        self.assertEqual(first.json()["support_count"], 1)

        # Second point à ~20 m à l'est, téléphone resté à ~15 m du point
        second = self.post_report(
            point_lat=6.3703,
            point_lng=2.391381,
            device_lat=6.3704,
            device_lng=2.3913,
            photo=photo_file(color="red"),  # photo différente : la vérification 6 (empreinte) tourne avant celle-ci
        )
        self.assertEqual(second.status_code, 200, second.content)
        body = second.json()
        self.assertTrue(body["duplicate"])
        self.assertEqual(body["support_count"], 2)
        self.assertEqual(body["tracking_code"], first.json()["tracking_code"])
        self.assertEqual(Report.objects.count(), 1)
        self.assertEqual(Report.objects.get().support_count, 2)

    def test_far_same_category_creates_a_new_report(self):
        self.assertEqual(self.post_report().status_code, 201)

        # Second point à ~200 m à l'est : hors du rayon de 30 m
        second = self.post_report(
            point_lat=6.3703,
            point_lng=2.393008,
            device_lat=6.3704,
            device_lng=2.3929,
            photo=photo_file(color="red"),
        )
        self.assertEqual(second.status_code, 201, second.content)
        body = second.json()
        self.assertFalse(body["duplicate"])
        self.assertEqual(body["support_count"], 1)
        self.assertEqual(Report.objects.count(), 2)

    def test_different_category_is_not_a_duplicate(self):
        # Même point, mais catégorie différente : pas de fusion
        self.assertEqual(self.post_report().status_code, 201)  # dépôt sauvage

        second = self.post_report(category="caniveau_bouche", photo=photo_file(color="red"))
        self.assertEqual(second.status_code, 201, second.content)
        body = second.json()
        self.assertFalse(body["duplicate"])
        self.assertEqual(body["support_count"], 1)
        self.assertEqual(Report.objects.count(), 2)

    def test_old_report_is_not_a_duplicate(self):
        # Même point et même catégorie, mais le premier signalement a 40 jours
        # (fenêtre : DUPLICATE_DAYS = 30) : pas de fusion.
        self.assertEqual(self.post_report().status_code, 201)
        # created_at est auto_now_add : on le recule via l'update() du queryset
        old = Report.objects.get()
        Report.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=40))

        second = self.post_report(photo=photo_file(color="red"))
        self.assertEqual(second.status_code, 201, second.content)
        body = second.json()
        self.assertFalse(body["duplicate"])
        self.assertEqual(body["support_count"], 1)
        self.assertEqual(Report.objects.count(), 2)


class PhotoContentCheckTest(ApiTestCase):
    """Vérification 7 : capture d'écran refusée, verdict enregistré en base (jamais renvoyé au public)."""

    def test_screenshot_is_rejected_and_nothing_is_saved(self):
        # Le client simulé (VERIFY_MODE=mock) reconnaît les captures d'écran au nom du fichier
        response = self.post_report(photo=photo_file(name="screenshot.jpg"))
        self.assertEqual(response.status_code, 422, response.content)
        error = response.json()["error"]
        self.assertEqual(error["code"], "PHOTO_SCREENSHOT")
        self.assertEqual(Report.objects.count(), 0)

    def test_verdict_is_saved_on_success(self):
        response = self.post_report()
        self.assertEqual(response.status_code, 201, response.content)
        verdict = Report.objects.get().ai_verdict
        self.assertEqual(
            sorted(verdict),
            [
                "confidence",
                "contains_identifiable_person",
                "is_public_outdoor_space",
                "is_screenshot_or_screen_photo",
                "matches_category",
                "reason",
            ],
        )
        self.assertTrue(verdict["matches_category"])
        self.assertFalse(verdict["is_screenshot_or_screen_photo"])
        self.assertEqual(verdict["confidence"], 0.9)

    def test_low_confidence_is_rejected(self):
        # Confiance 0,4 < seuil 0,6 (AI_MIN_CONFIDENCE) : refus
        with patch(
            "verification.vision.get_client", return_value=FakeVisionClient(fake_verdict(confidence=0.4))
        ):
            response = self.post_report()
        self.assertEqual(response.status_code, 422, response.content)
        self.assertEqual(response.json()["error"]["code"], "PHOTO_MISMATCH")
        self.assertEqual(Report.objects.count(), 0)

    def test_category_mismatch_is_rejected(self):
        # La photo ne correspond pas à la catégorie déclarée (confiance haute, ça ne change rien)
        with patch(
            "verification.vision.get_client",
            return_value=FakeVisionClient(fake_verdict(matches_category=False)),
        ):
            response = self.post_report()
        self.assertEqual(response.status_code, 422, response.content)
        self.assertEqual(response.json()["error"]["code"], "PHOTO_MISMATCH")
        self.assertEqual(Report.objects.count(), 0)

    def test_confidence_at_threshold_is_accepted(self):
        # Confiance exactement égale au seuil : « ≥ 0,6 » est accepté
        with patch(
            "verification.vision.get_client", return_value=FakeVisionClient(fake_verdict(confidence=0.6))
        ):
            response = self.post_report()
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Report.objects.get().ai_verdict["confidence"], 0.6)