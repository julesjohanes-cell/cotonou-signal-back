import hashlib
import hmac
import json

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from reports.utils import normalize_text, reporter_ref

from .client import mask_number
from .handlers import iter_text_messages
from .signature import verify_signature

SECRET = "secret-de-test"
URL = "/api/v1/webhooks/whatsapp"

PAYLOAD = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {"from": "22990000000", "type": "text", "text": {"body": " Signaler "}},
                            {"from": "22990000000", "type": "image"},
                        ]
                    }
                },
                {"value": {"statuses": [{"status": "delivered"}]}},
            ]
        }
    ]
}


def sign(body, secret=SECRET):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class HelpersTest(SimpleTestCase):
    def test_signature(self):
        body = b'{"a": 1}'
        self.assertTrue(verify_signature(body, sign(body), SECRET))
        self.assertFalse(verify_signature(body, sign(body, "autre"), SECRET))
        self.assertFalse(verify_signature(body, "", SECRET))
        self.assertFalse(verify_signature(body, sign(body), ""))

    def test_text_messages_only(self):
        self.assertEqual(list(iter_text_messages(PAYLOAD)), [("22990000000", " Signaler ")])
        self.assertEqual(list(iter_text_messages({})), [])

    def test_normalize_and_masking(self):
        self.assertEqual(normalize_text("  SIGNALÉR  "), "signaler")
        self.assertEqual(mask_number("22990000000"), "229****0000")

    @override_settings(REPORTER_HMAC_KEY="k")
    def test_reporter_ref_is_stable_and_hides_the_number(self):
        ref = reporter_ref("+229 90 00 00 00")
        self.assertEqual(ref, reporter_ref("22990000000"))
        self.assertNotIn("90000000", ref)
        self.assertEqual(reporter_ref(""), "")


@override_settings(WHATSAPP_VERIFY_TOKEN="jeton")
class WebhookTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_verification_handshake(self):
        ok = self.client.get(URL, {"hub.mode": "subscribe", "hub.verify_token": "jeton", "hub.challenge": "12345"})
        self.assertEqual((ok.status_code, ok.content), (200, b"12345"))
        bad = self.client.get(URL, {"hub.mode": "subscribe", "hub.verify_token": "faux", "hub.challenge": "1"})
        self.assertEqual(bad.status_code, 403)

    @override_settings(WHATSAPP_MODE="mock", WHATSAPP_APP_SECRET="")
    def test_mock_mode_accepts_unsigned_requests(self):
        response = self.client.post(URL, PAYLOAD, format="json")
        self.assertEqual(response.status_code, 200)

    @override_settings(WHATSAPP_MODE="live", WHATSAPP_APP_SECRET=SECRET)
    def test_live_mode_requires_a_valid_signature(self):
        body = json.dumps(PAYLOAD).encode()
        unsigned = self.client.post(URL, body, content_type="application/json")
        self.assertEqual(unsigned.status_code, 403)
        forged = self.client.post(URL, body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=sign(body, "autre"))
        self.assertEqual(forged.status_code, 403)
        signed = self.client.post(URL, body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=sign(body))
        self.assertEqual(signed.status_code, 200)

    @override_settings(WHATSAPP_MODE="mock", WHATSAPP_APP_SECRET=SECRET)
    def test_a_configured_secret_is_always_enforced(self):
        response = self.client.post(URL, PAYLOAD, format="json")
        self.assertEqual(response.status_code, 403)
