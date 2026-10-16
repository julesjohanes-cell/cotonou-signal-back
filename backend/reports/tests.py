"""
Tests de l'API. Lancer :  docker compose exec web python manage.py test

Ces tests servent de MODÈLE : un test par code d'erreur du contrat, le parcours réussi, et la protection des
données privées. Ajoutez un test dès que vous implémentez une vérification.
"""

import io
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from .geo import haversine_m, in_cotonou_bbox
from .models import CaptureSession, Category, Report

API = "/api/v1"
# Un point dans Cotonou et la position du téléphone, à ~15 m
POINT = {"point_lat": 6.3703, "point_lng": 2.3912}
DEVICE = {"device_lat": 6.3704, "device_lng": 2.3911, "device_accuracy_m": 12}

PRIVATE_FIELDS = ["reporter_location", "reporter_ref", "ai_verdict", "distance_m", "device_lat", "device_lng"]


def photo_file(name="photo.jpg", color="green"):
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), color).save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class GeoHelpersTest(SimpleTestCase):
    def test_haversine_one_degree_of_latitude_is_about_111_km(self):
        self.assertAlmostEqual(haversine_m(6.0, 2.4, 7.0, 2.4) / 1000, 111.2, delta=0.3)

    def test_haversine_same_point_is_zero(self):
        self.assertEqual(haversine_m(6.37, 2.39, 6.37, 2.39), 0)

    def test_bbox(self):
        self.assertTrue(in_cotonou_bbox(6.3703, 2.3912))
        self.assertFalse(in_cotonou_bbox(9.3077, 2.3158))  # Parakou


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="cotonou-test-media-"))
class ApiTestCase(TestCase):
    fixtures = ["categories"]

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        from django.conf import settings

        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()

    def post_report(self, category="depot_sauvage", **overrides):
        data = {"category": category, "description": "Test", **POINT, **DEVICE, "photo": photo_file()}
        data.update(overrides)
        return self.client.post(f"{API}/reports", data, format="multipart")


class PublicEndpointsTest(ApiTestCase):
    def test_health(self):
        response = self.client.get(f"{API}/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertIn("postgis", response.json())

    def test_categories_lists_nine_with_services(self):
        data = self.client.get(f"{API}/categories").json()
        self.assertEqual(len(data), 9)
        burning = next(c for c in data if c["slug"] == "brulage_dechets")
        self.assertEqual(sorted(burning["services"]), ["Collecte des déchets", "Environnement"])
        other = next(c for c in data if c["slug"] == "autre")
        self.assertTrue(other["needs_moderation"])

    def test_trailing_slash_is_accepted(self):
        self.assertEqual(self.client.get(f"{API}/categories/").status_code, 200)


class CreateReportTest(ApiTestCase):
    def test_happy_path_publishes(self):
        response = self.post_report()
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["status"], "published")
        self.assertFalse(body["duplicate"])
        self.assertEqual(body["support_count"], 1)
        self.assertRegex(body["tracking_code"], r"^CS-[2-9A-HJKMNP-Z]{6}$")

        report = Report.objects.get(tracking_code=body["tracking_code"])
        self.assertEqual(len(report.photo_sha256), 64)
        self.assertAlmostEqual(report.location.x, 2.3912)  # x = longitude
        self.assertAlmostEqual(report.location.y, 6.3703)  # y = latitude
        self.assertLess(report.distance_m, 30)
        self.assertEqual(report.history.count(), 1)

    def test_autre_goes_to_moderation_and_is_not_on_the_map(self):
        response = self.post_report(category="autre")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "moderation")
        features = self.client.get(f"{API}/reports").json()["features"]
        self.assertEqual(features, [])

    def test_too_far_is_rejected_with_details_and_nothing_is_saved(self):
        # téléphone à ~500 m du point
        response = self.post_report(device_lat=6.3748)
        self.assertEqual(response.status_code, 422)
        error = response.json()["error"]
        self.assertEqual(error["code"], "TOO_FAR")
        self.assertGreater(error["details"]["distance_m"], 100)
        self.assertEqual(Report.objects.count(), 0)

    def test_inaccurate_gps_is_rejected_with_details(self):
        # B-1: Précision à 80 m (> 50 m)
        response = self.post_report(device_accuracy_m=80)
        self.assertEqual(response.status_code, 422)
        error = response.json()["error"]
        self.assertEqual(error["code"], "GPS_INACCURATE")
        self.assertEqual(error["details"]["accuracy_m"], 80)
        self.assertEqual(error["details"]["max_m"], 50)
        self.assertEqual(Report.objects.count(), 0)

    def test_out_of_zone_is_rejected_with_details(self):
        # B-2: Téléphone à Ouidah (hors de Cotonou)
        response = self.post_report(
            point_lat=6.36, point_lng=2.08, device_lat=6.36, device_lng=2.08
        )
        self.assertEqual(response.status_code, 422)
        error = response.json()["error"]
        self.assertEqual(error["code"], "OUT_OF_ZONE")
        self.assertEqual(error["details"]["device_lat"], 6.36)
        self.assertEqual(error["details"]["device_lng"], 2.08)
        self.assertEqual(Report.objects.count(), 0)

    def test_corrupted_photo_gives_photo_invalid(self):
        # B-3: Fichier texte renommé en .jpg (corrompu/illisible)
        bad_photo = SimpleUploadedFile("fake.jpg", b"ceci n'est pas une image", content_type="image/jpeg")
        response = self.post_report(photo=bad_photo)
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["error"]["code"], "PHOTO_INVALID")
        self.assertEqual(Report.objects.count(), 0)

    def test_unsupported_photo_format_gives_photo_invalid(self):
        # B-3: Format BMP non autorisé (seuls JPEG, PNG, WEBP sont acceptés)
        buffer = io.BytesIO()
        Image.new("RGB", (64, 48), "blue").save(buffer, format="BMP")
        bmp_photo = SimpleUploadedFile("image.bmp", buffer.getvalue(), content_type="image/bmp")
        response = self.post_report(photo=bmp_photo)
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["error"]["code"], "PHOTO_INVALID")
        self.assertEqual(Report.objects.count(), 0)

    def test_oversized_photo_gives_photo_invalid(self):
        # B-3: Fichier de plus de 8 Mo
        huge_data = b"x" * (9 * 1024 * 1024)
        huge_photo = SimpleUploadedFile("huge.jpg", huge_data, content_type="image/jpeg")
        response = self.post_report(photo=huge_photo)
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["error"]["code"], "PHOTO_INVALID")
        self.assertEqual(Report.objects.count(), 0)

    def test_missing_fields_give_invalid_input(self):
        response = self.client.post(f"{API}/reports", {"category": "depot_sauvage"}, format="multipart")
        self.assertEqual(response.status_code, 400)
        error = response.json()["error"]
        self.assertEqual(error["code"], "INVALID_INPUT")
        self.assertIn("photo", error["details"]["fields"])

    def test_unknown_category_gives_invalid_input(self):
        response = self.post_report(category="nimporte_quoi")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_INPUT")


class CaptureTokenTest(ApiTestCase):
    def test_create_and_check_session(self):
        created = self.client.post(f"{API}/capture-sessions")
        self.assertEqual(created.status_code, 201)
        token = created.json()["token"]
        self.assertTrue(created.json()["capture_url"].endswith(f"/capture/{token}"))
        self.assertEqual(self.client.get(f"{API}/capture-sessions/{token}").json()["valid"], True)

    def test_unknown_token_is_404(self):
        response = self.client.get(f"{API}/capture-sessions/inconnu")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

    def test_expired_token_is_410(self):
        session = CaptureSession.create_for()
        CaptureSession.objects.filter(pk=session.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.client.get(f"{API}/capture-sessions/{session.token}")
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json()["error"]["code"], "TOKEN_EXPIRED")

    def test_token_is_consumed_by_a_successful_report_only(self):
        session = CaptureSession.create_for()
        rejected = self.post_report(capture_token=session.token, device_lat=6.3748)
        self.assertEqual(rejected.status_code, 422)  # le lien n'est pas consommé par un rejet
        self.assertEqual(self.post_report(capture_token=session.token).status_code, 201)
        again = self.post_report(capture_token=session.token, photo=photo_file(color="red"))
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.json()["error"]["code"], "TOKEN_USED")

    @override_settings(REQUIRE_CAPTURE_TOKEN=True)
    def test_token_required_when_configured(self):
        response = self.post_report()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_INPUT")


class PrivacyTest(ApiTestCase):
    def test_public_endpoints_never_leak_private_fields(self):
        code = self.post_report().json()["tracking_code"]
        geojson = self.client.get(f"{API}/reports")
        detail = self.client.get(f"{API}/reports/{code}")
        for response in (geojson, detail):
            text = response.content.decode()
            for field in PRIVATE_FIELDS:
                self.assertNotIn(field, text, f"{field} ne doit jamais être public")

    def test_geojson_is_longitude_first(self):
        self.post_report()
        feature = self.client.get(f"{API}/reports").json()["features"][0]
        lng, lat = feature["geometry"]["coordinates"]
        self.assertAlmostEqual(lng, 2.3912)
        self.assertAlmostEqual(lat, 6.3703)

    def test_geojson_filters(self):
        self.post_report(category="depot_sauvage")
        self.post_report(category="caniveau_bouche", photo=photo_file(color="blue"))
        only = self.client.get(f"{API}/reports", {"category": "caniveau_bouche"}).json()["features"]
        self.assertEqual([f["properties"]["category"] for f in only], ["caniveau_bouche"])
        inside = self.client.get(f"{API}/reports", {"bbox": "2.38,6.36,2.40,6.38"}).json()["features"]
        outside = self.client.get(f"{API}/reports", {"bbox": "2.50,6.40,2.51,6.41"}).json()["features"]
        self.assertEqual((len(inside), len(outside)), (2, 0))
        self.assertEqual(self.client.get(f"{API}/reports", {"bbox": "oups"}).status_code, 400)

    def test_unknown_tracking_code_is_404(self):
        response = self.client.get(f"{API}/reports/CS-ZZZZZZ")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")


class AgentTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        from django.contrib.auth.models import Group

        User = get_user_model()
        self.sanitation = User.objects.create_user("assainissement", password="pw-test-1234")
        self.sanitation.groups.add(Group.objects.get(name="Assainissement"))
        self.waste = User.objects.create_user("dechets", password="pw-test-1234")
        self.waste.groups.add(Group.objects.get(name="Collecte des déchets"))
        self.code = self.post_report(category="caniveau_bouche").json()["tracking_code"]

    def login(self, username, password="pw-test-1234"):
        response = self.client.post(f"{API}/auth/login", {"username": username, "password": password}, format="json")
        if response.status_code == 200:
            self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.json()['token']}")
        return response

    def test_login_wrong_password(self):
        response = self.login("assainissement", "mauvais")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHENTICATED")

    def test_login_returns_token_and_services(self):
        response = self.login("assainissement")
        self.assertEqual(response.json()["user"]["services"], ["Assainissement"])

    def test_agent_endpoints_require_login(self):
        response = self.client.get(f"{API}/agent/reports")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHENTICATED")

    def test_agent_sees_only_their_services(self):
        self.login("dechets")
        self.assertEqual(self.client.get(f"{API}/agent/reports").json()["count"], 0)
        self.login("assainissement")
        data = self.client.get(f"{API}/agent/reports").json()
        self.assertEqual(data["count"], 1)
        self.assertIn("ai_verdict", data["results"][0])  # visible des agents
        self.assertNotIn("reporter_location", str(data))

    def test_other_service_cannot_change_status(self):
        self.login("dechets")
        response = self.client.patch(f"{API}/agent/reports/{self.code}", {"status": "in_progress"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "FORBIDDEN")

    def test_full_lifecycle_and_invalid_transition(self):
        self.login("assainissement")
        url = f"{API}/agent/reports/{self.code}"

        skip = self.client.patch(url, {"status": "resolved"}, format="json")
        self.assertEqual(skip.status_code, 409)
        self.assertEqual(skip.json()["error"]["code"], "INVALID_TRANSITION")

        started = self.client.patch(url, {"status": "in_progress", "note": "Équipe envoyée"}, format="json")
        self.assertEqual(started.status_code, 200, started.content)
        self.assertEqual(started.json()["status"], "in_progress")

        after = self.client.post(f"{url}/after-photo", {"photo": photo_file("apres.jpg", "blue"), "note": "Curé"}, format="multipart")
        self.assertEqual(after.status_code, 200, after.content)
        self.assertEqual(after.json()["status"], "resolved")
        self.assertTrue(after.json()["photo_after_url"])

        public = self.client.get(f"{API}/reports/{self.code}").json()
        self.assertEqual([h["to_status"] for h in public["history"]], ["published", "in_progress", "resolved"])
        self.assertNotIn("agent", str(public["history"]))

    def test_invalid_status_value(self):
        self.login("assainissement")
        response = self.client.patch(f"{API}/agent/reports/{self.code}", {"status": "published"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_INPUT")
