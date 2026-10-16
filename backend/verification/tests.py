"""
Tests de la vérification 8 — doublon (ÉQUIPE 5). Lancer :  docker compose exec web python manage.py test verification

La base de tests est réutilisée depuis reports/tests.py (ApiTestCase, photo_file) pour ne pas dupliquer
les aides d'envoi. Les coordonnées repartent de POINT : à 6° de latitude, 1° de longitude ≈ 110 600 m,
donc Δlng ≈ 0,00018 ≈ 20 m et Δlng ≈ 0,0018 ≈ 200 m.
"""

from reports.models import Report
from reports.tests import ApiTestCase, photo_file


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